---
name: tech-spec-writer
description: Turn a product-written Jira ticket — its acceptance criteria, specs and comments — into a developer-approved Technical Specification grounded in the current branch's source code and data/migration scripts, then write it back to Jira by updating the description, adding a comment, or creating a "[Tech Spec]" sub-task. Works with any repository, and builds up a per-project profile (references/projects/<project>.md) so later runs in the same project are more precise. Works with the developer to resolve every implementation decision the code raises before anything is filed. Use whenever a developer asks to write, draft, generate or refine a tech spec, technical specification, technical ACs, implementation plan or solution design for a Jira ticket, or to "convert the product ACs" or "spec out" a ticket before coding — even if they don't say "technical specification". Refuses without a ticket key. Does not change code.
argument-hint: <JIRA-KEY> [--mode comment|update|create] [--dry-run]
---

# tech-spec-writer

Converts what the product team wrote on a Jira ticket into a **Technical Specification** that a
later Claude session can implement from, and files it back to Jira. The flow is:

**read the ticket → read the code → draft → resolve open items with the developer → approve → write to Jira.**

The method is the same for every repository. What differs per project — where code lives, how
permissions are enforced, test conventions, release rules, domain gotchas — is kept in an optional
**project profile**, `references/projects/<project>.md` (step 0). The profile makes the skill more
accurate in a project it has seen before; the skill works without one.

The spec is the contract between the product intent and the code that will be written. A later
session will read it with `getJiraIssue` and implement it, usually without this conversation's
context. So everything that session needs to know — what the code does today, what must change,
what must not, and every decision the developer made — has to be in the spec itself, stated
precisely enough that two developers would build the same thing.

This skill **specifies**. It does not edit source, write tests, run builds, commit, or transition
the ticket. Reading code, `git log` and SQL scripts is expected; changing them is not.

The helper scripts under `scripts/` (relative to this SKILL.md's directory) only read files. Run
them with `python -I` (use `python3` only where `python` does not exist). `<repo>` is the working
repository's root.

**Everything it produces is in English** (Australian spelling), whatever language the conversation uses.

## Arguments

Parse the space-separated tokens from `$ARGUMENTS`:

1. `<ticket>` — **required**. A Jira key such as `PROJ-1234` (project prefix, hyphen, number).
2. `--mode comment|update|create` — where the approved spec goes. Default `comment`, because it is
   the only mode that leaves the product team's text exactly as they wrote it.
   - `update` — the ticket's description becomes the spec. The product team's original description
     is quoted verbatim under Background (see step 7), so nothing they wrote is lost from view.
   - `comment` — the spec is added as a comment on the ticket.
   - `create` — the spec becomes the description of a new Sub-task, `[Tech Spec] <ticket summary>`,
     under the ticket.
3. `--dry-run` — do everything up to and including the approval gate, but write nothing to Jira.
   Present the final spec in the conversation (or save it to a file if asked) and stop.

**No ticket key → refuse and stop.** Ask for one. Do not infer it from the branch name, a commit or
the conversation: the spec has to belong to a ticket, and guessing the wrong one writes a spec onto
someone else's work. Start the request with `[tech-spec-writer]` (see Rules).

Invoked automatically (without the developer typing the command)? Confirm the ticket key and mode
with the developer, in a message starting with `[tech-spec-writer]`, before reading further, then continue as normal. The approval gate in step 6
applies however the skill was started.

## Steps

### 0. Pre-flight: check the MCP tools

Do this after parsing the arguments and before reading anything else.

**Jira MCP — required.** The skill reads the ticket and, outside a dry run, writes the spec back,
so it cannot do its job without Jira. Check two things:

1. **Installed and available**: the Atlassian/Jira tools (`getJiraIssue`, `getAccessibleAtlassianResources`, …)
   are in this session, either loaded or listed as deferred tools you can load with `ToolSearch`.
2. **Authenticated and authorised**: call `getAccessibleAtlassianResources` and confirm it returns
   at least one site. An auth error, a server that is still waiting for authentication, or an
   empty list all count as failure. Keep the list: step 1 picks the ticket's site from it.

If either check fails, **stop and do not run the skill.** In a message starting with
`[tech-spec-writer]` (see Rules), tell the developer politely that the Jira
MCP is required. Say which check failed, and give them the short setup steps in
[references/mcp-setup.md](references/mcp-setup.md#jira-required), including how to set the Jira API
token. Do not offer to proceed from pasted ticket text instead: a spec built from a paste cannot
be filed or re-read by the implementing session.

**Figma MCP — optional.** Check whether Figma tools are in the session (a server named `figma`, with
tools such as `get_metadata`, `get_screenshot` or `get_design_context`) and authorised. Do the check,
because step 1 depends on it: search the deferred tools with `ToolSearch` (query `figma`) and look for
an authentication notice. The result is always one of **available**, **installed but not authorised**
or **not installed**, never "not checked".

- **Available**: in step 1, inspect every Figma link or design on the ticket, its comments and its
  parent epic (load a Figma skill first if one says it must be). Treat what you find as product
  requirements, numbered with the rest, and cite the Figma node in the spec.
- **Not authorised or not installed**: carry on. Treat Figma links as sources you cannot read (step 1),
  and say once in the report that installing or authorising the Figma MCP would let the skill read
  them ([references/mcp-setup.md](references/mcp-setup.md#figma-optional)).

**Project profile — after the MCP checks.** The profile holds what is specific to this repository.
Identify the project from the repository root folder name (`git rev-parse --show-toplevel`) and the
`origin` remote name if any. Read the front matter of each profile in `references/projects/` (ignore
`_template.md`) and in `<repo>/.claude/tech-spec-writer/` if that exists (the fallback location, see
step 2): it matches when one of its `detect-paths` exists under the repository root, or its `name`
equals the folder or remote name (ignoring case, `-`/`_`). If both locations hold the same profile,
use the one in `references/projects/`.

- **A profile matches**: read it in full and use it as the project's code map, conventions and
  examples. It is a starting map, not evidence: confirm what it says on the current branch (step 2);
  where the branch disagrees, the branch wins and the profile is corrected (end of step 2).
- **No profile matches**: carry on generically and create one after reading the code (end of step 2),
  without stopping to ask.

Tell the developer the result in one line before step 1, for example "Jira MCP: connected. Figma MCP:
not installed, so Figma links will be listed as unread. Project profile: <name>." (or "Project profile:
none yet, will create `acme-shop.md` after reading the code.")

### 1. Read the ticket

`getJiraIssue` with `view: "evidence"`. Choose the site (cloudId) in this order: the profile's
`jira-cloud-id` if it covers the ticket's project key; the only site from step 0 if there is one;
otherwise try the `getJiraIssue` call on each accessible site until the ticket is found. The wrong
site is the usual reason the call fails. Once found, note the site in the project profile if it is
not there already.
Then read the comments (`listJiraIssueComments` via `discover` if `getJiraIssue` only reports a
count) and the parent epic's summary and description — the epic often states the wider goal and
what sibling tickets cover, which is how you know what is out of scope here.

Collect, in your own notes:

- **Product ACs and specs** — the requirements you must satisfy. Number them `P1, P2, …` in the
  order the product team wrote them, so every technical AC can trace back to one. Include what the
  description and its tables say, not only the AC table: an "Applies to: Online files" row or a
  stored-items table is a requirement or a scope boundary too, and the spec must say so explicitly
  (a boundary becomes an out-of-scope line, e.g. "desktop company files").
- **Scope signals** — "this ticket covers…", "separate ticket for…", sibling tickets in the epic,
  comments that move or drop a requirement. Comments often carry the real scope.
- **Answers to the ticket's own open questions.** For every marker such as **[TO CONFIRM Qn]**,
  "proposal:" or "still open", look the question up everywhere before treating it as open: the Open
  points / questions table (including its "Who answers" or notes cell, where product owners often
  append the answer, e.g. "PO - as in <other integration>, <role A> + <role B>"), dated decisions
  (D-31Oct), the comments, and the epic. Product teams answer in one place and leave the marker in
  others. When an answer exists:
  - it is a product requirement: number it like any other (cite where it was answered) and build on it;
  - read it with the proposal it answers and spell out what it means in this code; if the two differ,
    or the answer is too terse to apply, that difference is an open item for the developer, not the
    product team;
  - note in Background, in one line, every place the marker still reads as open (for example "AC9
    still says TO CONFIRM Q31; answered in Open points"), so the product team can tidy the ticket.

  Only a question with no answer anywhere stays waiting on the product team (step 5). To find them
  mechanically, save the description (and comments) to a file in your scratch directory and run
  `python -I ${CLAUDE_PLUGIN_ROOT}/skills/tech-spec-writer/scripts/ticket_questions.py <file>`: it lists,
  per question id, every TO CONFIRM place, its open-points row and the "who answers" cell, flagging
  cells that hold more than role names as a possible answer. The flag means "look here", not
  "answered"; read each flagged cell yourself.
- **Figma designs** — with the Figma MCP available (step 0), open each linked design and add what
  it shows to the product requirements.
- **What you cannot read** — screenshots, attachments, and Figma links when the Figma MCP is not
  available. Say so plainly and list them as an open item if they hold a requirement you need.
- **An existing spec** — look in all three places whatever `--mode` was given: the ticket's
  description, its comments, and its sub-tasks (`getJiraIssue`, `listJiraIssueComments`, and the
  sub-task list). A spec is any text carrying the marker line `tech-spec-writer: <KEY> | product-rev
  <8 hex> | v<skill version> | <date>` (step 7), or, for specs written before markers existed, a
  description in this format, a comment headed `# Technical Specification`, or a `[Tech Spec]`
  sub-task. Tell the developer where you found it.
  - **One found:** this run **revises** it rather than starting over: keep its decisions, re-verify
    its "Current logic", and change only what the code, the developer or the changed product text
    now says differently. Update it where it lives, even if `--mode` names another place; say so.
  - **More than one, or in a place other than the requested mode:** ask which to update, in a
    `[tech-spec-writer]` message, and never file a second copy.
  - **Did the product text change?** Save the description plus every comment except the spec's own
    comment to a file, run `python -I ${CLAUDE_PLUGIN_ROOT}/skills/tech-spec-writer/scripts/product_hash.py <file>`,
    and compare with the marker's `product-rev`. Equal: say the product text is unchanged and
    re-verify the code only. Different: read the ticket's changelog (`getJiraIssue` with the
    changelog expanded, or `executeRead`) for the old and new text, give the developer a short
    "what changed" summary, then revise only the rules, ACs, plan steps and open items that depend on
    the change. A decision the developer made stays unless the change invalidates it; then it goes
    back to Open items with a note saying why. If the changelog cannot be read, compare the
    product requirements with the existing spec's numbered list and say the comparison is by text.
    A spec with no marker has no stored revision: treat the product text as possibly changed.

If a Jira call fails here despite the pre-flight check (for example the token expired, or there is
no permission on this ticket), stop and tell the developer what failed, as in step 0.

Ignore the ticket's status. "Done" or "QA Passed" says nothing about what the code does.

### 2. Read the code — on the current branch

The spec describes changes to **the branch checked out now**, whatever it is. Record where you are:

```bash
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
git status --short          # uncommitted changes count as "current code"; mention them if relevant
git log --oneline -5 --grep="<TICKET>"   # any work already done for this ticket
```

Then find every surface the product requirements touch. Work outward from the nouns in the ACs —
screen names, labels, field names, config keys, endpoints, integration or vendor names, report
names. With a project profile, start from its code map; without one, discover the layout from the
repository's top level, build files and READMEs. Cover each layer the requirement could reach:

- **Frontend** — screens, routes and API clients the requirement names.
- **API** — handlers or routes. **Authorisation** is often outside the handler (a filter chain,
  middleware, gateway or security config rather than annotations): find where this project enforces it.
- **Services and logic** — what sits behind those endpoints, including background jobs and other callers.
- **Data access** — queries, mappers, ORM models and shared fragments that reach other statements; follow them.
- **Schema and data** — migrations, release and ticket scripts, seed data, config metadata: "current
  logic" as much as application code.
- **Tests** — existing tests for each class you will change, so the plan can say which must be updated.

Search with `python -I ${CLAUDE_PLUGIN_ROOT}/skills/tech-spec-writer/scripts/search.py <pattern> --repo <repo> [--path <dir>] [--glob '<pattern>']
[-w] [-F] [-l]` rather than `grep -r`. It searches tracked files only (never `node_modules` or build
output), cuts long lines and caps the output, telling you how many matches it did not show; narrow
with `--path`/`--glob` instead of raising `--max`. An unscoped recursive grep of a large source tree
can walk vendored dependencies and return megabytes.

Put independent lookups (several searches, `git` checks, or file reads that do not depend on each
other) in one command or one parallel batch instead of one call each; every extra call re-reads the
whole conversation. Read a large file by line range or after locating the symbol, unless you need the
whole class to explain what it does.

Read the code until you can explain, for each requirement, **what happens today and why**. Keep a
map of concern → class/statement/script. This is the most valuable thing you produce: product ACs
describe intent, and almost every real decision in a spec comes from something the code does that
the product team did not know about — a second caller, a layered lookup, a company-level fallback,
encrypted values, a cache, a sibling feature sharing the same table.

Mind the domain gotchas the repository documents (`CLAUDE.md`, `AGENTS.md`, a README or contributing
guide) and those in the project profile. A spec that repeats a known wrong assumption sends the next
session straight into a known bug.

**If you cannot find the surface a requirement names, do not guess.** Record it as an open item
with what you searched for.

**Follow every reference to existing behaviour into the code.** Tickets often state a requirement
by pointing at something that already exists: "as in <another integration>", "same as PD-nnnn",
"like the existing <feature>", "follow the <name> pattern", "reuse …". The requirement is then
whatever that code does, not the ticket's paraphrase of it. For each such reference:

- find the code that implements the referenced behaviour (search for the named feature, read the
  referenced ticket's commits with `git log --grep=<key>`) and state what it actually does, with
  evidence, in Current logic;
- name where this ticket's situation differs from the reference (different data, a missing stored
  value, another module or role), because that difference is usually where the open question is;
- on any open item the reference bears on, include "copy the reference behaviour as it is" as an
  option, described in this ticket's terms, even when you recommend something else.

If you cannot find the referenced behaviour, say what you searched for and raise it as an open
item. Never conclude "there is nothing to copy" without having read the reference's code path.

**Tell the developer when the ticket's ACs are not on this branch.** The spec describes this branch,
so the developer must know early if the ticket's world is not in it: they may have the wrong branch
checked out. After reading the code, check everything the ACs, epic or comments depend on or point at:
a feature or ticket they build on ("PD-nnnn", "as in <X>", a dependency, a sibling), and any class,
field, config key or screen they name. Mark an item **missing** only after searching the code and scripts.

For each missing item, find where it lives, read-only: `git log --all --oneline --grep="<KEY>"` and
`git branch -a --contains <sha>`; `git merge-base --is-ancestor <sha> HEAD` to confirm it is not in
HEAD; `git show <sha>` or `git grep <name> <ref>` to read it there. Read what it adds to the data model
(fields, columns, config rows) as well as the logic, because a missing field is often the real constraint.

Then tell the developer **before drafting further**, in a `[tech-spec-writer]` notice (not a gate: carry
on unless they answer). Name each missing item, the ticket or AC that needs it, and where it lives
(branch and commit, or "not found in any ref"); when it is on another branch, suggest switching to it or
rebasing. Example: `[tech-spec-writer] The ACs build on PROJ-123 (scheduled token refresh). It is not on
<branch>; it is on <other-branch> (<sha>). Check you are on the right branch.`

Keep the facts in the spec too: Background says what is missing and where it lives; Current logic
describes only this branch (anything read on another ref is labelled "reference only"); anything the
spec must rely on before it exists becomes a rule or plan step ("rebase onto X first") or an open item.

**Create or refresh the project profile.** This is the only file the skill writes besides the spec.
Write it to the skill's own `references/projects/`. If the developer cannot write there (a read-only or
managed plugin install: creating the file fails with a permission error), write it to
`<repo>/.claude/tech-spec-writer/<project-slug>.md` instead. An existing profile is refreshed where it
was found.

- **No profile matched (step 0)**: create `references/projects/<project-slug>.md` (slug = repository
  folder name, lowercase with hyphens) from
  [references/projects/_template.md](references/projects/_template.md). Fill in only what you read and
  confirmed in this run: Jira site and project key, code map with real paths, where authorisation is
  enforced, test frameworks and gates, migration/release locations, documented gotchas. Leave a section
  out rather than guess. Set `detect-paths` to one or two paths that exist only in this repository.
- **A profile matched: keep it current on every run.** The next run may be another ticket on another
  branch, so the profile may be updated, changed or overwritten as a whole to match what this run
  verified on this ticket and branch, rather than appended to. Correct lines now shown wrong (a moved
  path, a changed convention, a Jira project key, a role or term mapping, a gotcha), add what the next
  run would otherwise rediscover, and drop what is stale, unconfirmed or no longer earns its space.
  Keep it small: aim for under about 120 lines, with worked examples cut to one or two short excerpts. Overwrite the front-matter line `last-verified: <branch> @ <sha>, <date>` each time. If
  nothing needs changing, leave the file untouched.
  Judge against the code first: a ticket that asks for something the code does differently is a spec
  question (open item), not a profile error. A fact true only on some branches (a feature that exists on
  one) stays only if it is worth knowing, labelled with its branch; otherwise leave it out.
- Never write customer data or credentials into a profile, and keep out ticket text that the spec
  already holds.
- Tell the developer in one line what you created or updated and where (`[tech-spec-writer] Created
  references/projects/acme-shop.md`). This is a notice, not a gate. When the file went into the
  repository's `.claude/tech-spec-writer/`, say that it is a new untracked file there and that they can
  commit it or add it to `.git/info/exclude`; change no other repository file (not `.gitignore`).
- With `--dry-run`, the profile in the skill's directory is still written (it changes no repository file
  and no Jira content). A dry run never writes into the repository: if the skill's directory is not
  writable, put the profile text in the conversation instead. Do the same if neither location is writable.

### 3. Draft the spec

Write the draft in the structure in `references/spec-template.md` — read that file now; it explains
each section. If the project profile has worked examples, read those too: they show the house style.
Use exactly these sections, in this order, in every version (draft and final): Rules comes before
Current logic, and no other `##` sections are added, in particular no "Decisions" section (see step 5).

1. **Background** — the problem in technical terms, and the original product text (quoted in `update` mode).
2. **Rules** — numbered invariants the solution must keep. ACs cite them.
3. **Current logic (verified in code and data scripts, `<branch>` @ `<sha>`, `<date>`)** — what the
   code and data do today, only what you read and confirmed.
4. **Topic sections** — only when the ticket needs one (for example "Encryption").
5. **Scope** — in scope / out of scope, explicit.
6. **Acceptance Criteria** — technical, numbered `AC1…`, each verifiable, each citing its rules.
7. **Spec / Implementation Plan** — ordered work items naming the classes, statements, scripts and
   tests involved, no line numbers.
8. **Review Focus** — ways this change could go wrong, each ending "Guarded by …".
9. **Open items** — decisions still needed.

Write plainly and precisely. Every statement in "Current logic" must be something you read in the code or data scripts.
**Nothing stays "not confirmed".** When you infer something, try to confirm it first (read the class,
follow the call, search the scripts) and state it with its evidence. If the code cannot confirm it
(deployed configuration, live data, another repository, a third-party system's behaviour), make it an
open item saying what you checked, what is unknown and how the developer could check it, and point to
it from the claim ("see open item 3"). This applies to every section: no rule, AC, plan step or Review
Focus item may rest on an unconfirmed claim. Every technical AC must trace to a product requirement
(`P1…`), a rule, or a code finding. Do not invent requirements; if the code suggests something the
product team did not ask for, it is an open item, not an AC.

**Show evidence where a reader would otherwise have to take your word for it.** The developer
deciding an open item, and the reviewer approving the spec, need to see *why* you believe a finding,
especially a surprising one or one an AC rests on. Point at where it lives, and when the exact
expression is the point, quote the few characters that prove it:

> Found: `Order.customerId` is part of the table's composite key —
> `OrderEntity.getKey()` is `buildKey(type, customerId, createdAt)`.

Quote the line that proves *this* claim: a similar-looking line nearby (here, a sibling
`buildLookupKey` with no `customerId`) proves something else, and a reviewer who opens the file will
notice. Most statements need only the class or script name; a snippet earns its place only when it
settles a question the reader would otherwise open the file to answer. Keep snippets to one line or
one short expression: a quoted method body means you are explaining code rather than specifying a change.

**Name which one you mean when a term has more than one meaning in this change.** "User ID" can be
the user who connected, the user who triggered an action, or the `userId` key attribute; "status" a
stored column or a derived value; "integration" the row or the external connection. When the spec uses
such a term in more than one sense, every rule, AC and plan step that mentions it says which one, by
role and field (`TokenRefreshRequest.userId`, the acting user), and where two senses sit close together
it points at the other ("the connecting user's ID is stored on the token row, rule 10"). An implementer
reads a rule on its own, so "a user ID passed in is used for logging only" next to "store the user ID"
reads as a contradiction even when both are right.

The reverse is **two terms for one thing** (the product says "workspace name", the vendor's API says
`orgName`, the setting is `vendor.org.name`). State the mapping once (Background or Current logic; a
small table is fine), say whether the values are really the same or only describe the same thing from
different sources (an admin-typed setting vs a value the external system returns), and use one term
from then on.

**Trace every person or role the ticket names to a code identity.** Tickets name people by role ("the
connecting Administrator", "the sync user", "the automated user", "the approver"), and each becomes a
recipient, a permission or a stored value, so treat the role as an assumption until the code backs it.
For each, find and state with evidence:

- **Which identity it is**: a login in this application, a user in an external system, a system or
  run-as login, the user on a queued action, or a configured address.
- **Where it is captured**: the endpoint or job where it first appears (for example the session user
  when the "connect" endpoint starts an authorisation flow).
- **Who can actually be it**: the roles that can reach that entry point, as this project enforces them
  (annotations, a filter chain, middleware, security config). The ticket says "Administrator"; the
  code may also admit support or finance users.
- **Whether it is stored, and where**, or only passed through and dropped.
- **Whether two identities are assumed to be one**: the application user who clicks Connect and the
  administrator who signs in at the external system are different accounts, and only one may be
  visible to this application.

Anything the code settles is a fact in Current logic. Anything it cannot settle (the ticket's role is
narrower than the roles the code admits, the identity is not stored, or the mapping between two
identities is assumed) is an open item.

**Comments and Javadoc are claims, not evidence.** When one explains why the code does something
("deliberately not persisted because…"), check the reason against the code paths and branch conditions
before relying on it. Quote it only with what you confirmed, and if the code disagrees (for example the
check it protects is only reached on a first connect), say so in Current logic. The project profile, if
any, may add project-specific examples and checks for the points above.

**Coverage check before moving on:** every product requirement `P1…Pn` maps to at least one AC or
to an explicit out-of-scope line, and every rule is cited by at least one AC, the Tests AC or a
Review Focus item — a rule nothing checks (often a "keep X as is" rule, such as an existing nonce or
guard) is easy to break unnoticed. List any requirement that does neither as an open item; give an
uncited rule an AC or Review Focus line.

**Check the draft mechanically** once it is saved, and fix everything reported before going on:

- `python -I ${CLAUDE_PLUGIN_ROOT}/skills/tech-spec-writer/scripts/check_spec.py <spec.md> --repo <repo>`: structure, references, coverage and
  the rules above. Write the ticket's own ACs as "product AC9" (or the P number).
- `python -I ${CLAUDE_PLUGIN_ROOT}/skills/tech-spec-writer/scripts/check_identifiers.py <spec.md> --repo <repo>`: every name in backticks exists
  on the branch. A reported name is a mistake, or new, in which case the spec says so.

Re-run both until they pass. They check form, not substance.

A requirement is **met by current code** only when the code does what it asks. If it asks for
something the code deliberately does differently (a guard, a comment saying "deliberately not
stored", a design another feature relies on), that is a conflict: an open item, never "treated as
satisfied", and never labelled a developer decision the developer did not make.

### 4. Identify the open items

An open item is a decision the developer must make because the code allows more than one
reasonable solution, or because the product text is ambiguous or contradicts what the code does.
Typical sources:

- the product AC conflicts with existing behaviour, or would break another feature sharing the code,
  including logic the code chose on purpose (the product asks to store a value the code deliberately
  does not store, because a guard compares it or another lookup relies on it). Show the conflicting
  line and let the developer decide.
- more than one place implements the same rule (FE and BE, two services, two mappers)
- existing data would not satisfy the new rule — a migration, backfill or default is needed
- a requirement is silent on an edge case the code must handle (empty, null, deleted, multi-currency,
  multi-company, permissions, existing records)
- a choice of approach with real trade-offs (new service vs extending one, schema change vs config)
- release ordering, feature flags, or tenant-wide / global data
- something you could not read or find

For each, write: **the question**, **what you found** (with the class/script, and a snippet where it
is the evidence), **the options**, and **your recommendation with the reason**. All four, for every
item — including the minor ones and the ones about something you could not read. A recommendation
without a reason ("Recommended: (a).") gives the developer nothing to weigh, and is the most common
way these items fall short. For an unreadable source (a Figma link without the Figma MCP, a design
ticket you could not open), the options are what the spec would do under each plausible reading, and the recommendation
may be "ask the product team before deciding" — with the reason.

Also give each item a **Consequence** tag: High (blocks the ticket's purpose, or changes what a
customer sees or receives, stored data, or a security/data-loss risk), Medium, or Low (a detail the
spec can absorb either way), with one line saying why. Number the items from High to Low, so that
"the most consequential" and "the least consequential" item mean item 1 and the last item.

**Write open items, and every question you put to the developer, the way you would say it to a
colleague, in plainer language than the rest of the spec.** This is the one part a person must
understand quickly and answer, so it is read, not scanned.

- Open with the question in everyday words ("Who should we record as the person who connected?"),
  not a label or a field name. Keep the exact class, column or setting for the "Found" line, with a few
  words on what it does, so a developer who has not read that code can still follow.
- Short sentences, active voice, one idea each. Say what happens to a user or to the data, not only
  what the code does. Spell out any abbreviation or ticket shorthand the first time.
- Do not use AC, rule or requirement numbers (P12, rule 4, AC7) in the question or the options; say
  what they mean. Cross-references are fine elsewhere in the spec.
- Describe each option as a result ("Keep the table as it is and add two new columns"), and write the
  recommendation as advice with its reason ("I'd go with (a) because …"). When the answer depends
  on something you could not read, say so plainly instead of hedging.
- Keep all four parts and every fact; plain wording replaces jargon, never evidence.

Make clear what **leaving things as they are** would mean, as one of the options where it is a
realistic choice: the developer may decide the change is not wanted at all.

Do not file trivia — if the code and the product text together leave only one sensible answer,
decide it and state it in the spec.

### 5. Resolve the open items with the developer

The developer owns the solution; your job is to put each decision in front of them with the evidence,
and then make the spec say exactly what they decided. This is a conversation, not a form.

Present the draft's shape briefly (sections and AC titles), then ask about the open items **one at
a time, most consequential first**, waiting for each answer: `AskUserQuestion` when the options are
discrete, plain conversation otherwise. Give the finding and the options, and say which you recommend
and why. Answers often change a later item, which is why they go one at a time; never batch several
into one message or call. Write each as a short, friendly message to a colleague (see the wording
rules in step 4), not a form. Start each with the `[tech-spec-writer]` prefix (see Rules), for example:

```
[tech-spec-writer] Before finalising the spec, please decide on open item 1 of 4:

1. **Who is recorded as the connecting user on a reconnect?**
   ...
```

The developer can answer in any of these ways, and each needs different handling:

- **Picks an option** (yours or another). Apply it.
- **Rejects every option** — they do not want this changed. That is a decision too: record it as an
  explicit out-of-scope line or a rule ("existing behaviour of X is kept"), and remove anything in the
  draft that assumed a change. Do not keep arguing for an option they turned down; if rejecting it
  leaves a real risk, say so once and add it to Review Focus.
- **Proposes their own solution.** Evaluate it before writing it in: check it against the code the
  same way you checked your own options — what it touches, whether it keeps the Rules, whether it
  breaks a caller, data or another feature you found. Then tell them plainly: it works as is; it works
  with an adjustment (say which and why); or it conflicts with something (show the evidence) and
  what they could do instead. They decide after hearing that. When their solution is sound, adopt it
  without hedging — it is often better than yours, because they know things the code does not show.
- **Refers to an item by description** ("the most consequential", "the least consequential", "the
  one about X"). Resolve it by the Consequence tags, and say in one line which item you took it to
  mean. An imperfect match is not a reason to leave the item open: pick the best match, state the
  assumption, and apply the decision. Never match a rejection ("keep current behaviour") to an item
  whose removal would defeat the ticket's purpose; take the best match among the others.
- **Asks you to look further.** Do it, report what you found, and re-ask.
- **Wants to leave it open** (for example, waiting on the product team). It stays in Open items with
  who or what it is waiting on — the only way an item survives this step.
- **Answers an item that is waiting on someone else** (the product team, or anyone but the
  developer). A blanket answer such as "take your recommendation for everything else" does not settle
  it, because the developer cannot answer for them. Settle only the part the developer owns. The
  waiting part stays in Open items as the open question with "Waiting on: product team" (or whoever),
  and no Rule, Scope line or AC may decide it meanwhile (for example by declaring it not implemented).
  It leaves Open items only when the developer passes on that party's answer or says to go ahead
  without it, and then the spec says so.
- **Gives a blanket answer** ("take your recommendation for the rest", "whatever you think"). It
  settles only low-impact items. These stay in Open items marked "Waiting on: developer (explicit
  decision needed; not settled by a blanket answer)", are each asked in their own message before the
  final spec is shown, and are never applied silently, when the recommendation:
  - departs from what the product team wrote or answered on the ticket (for example, a different
    email recipient from the one in the product owner's answer);
  - changes what a customer sees or receives (screens, emails, exports, error messages);
  - adds stored data or a schema change (a new column, attribute, config key or migration script); or
  - was raised by the skill's own risk checks (a conflict between an AC and the code, a security or
    data-loss concern, or a role the code cannot map).

After each decision, **update the spec, not just the list**: the decision becomes a rule, an AC, a
scope line, a plan step or a Review Focus item, and the item leaves Open items. Then fix what it
touches elsewhere (an AC that assumed another option, a plan step now unnecessary, a risk that no
longer applies). Before adding a rule, look for an existing one on the same subject and merge the
decision into it, keeping every detail of both (condition, value, exception, citation); do not add a
near-duplicate or overwrite the old rule. If two existing rules overlap, merge them into the earlier
one, remove the later one, and update every AC, plan step and Review Focus item that cited a changed
rule number. A decision recorded only in the chat is lost to the session that implements the spec, and
a separate log of decisions (a "Decisions" section, table or subsection) repeats the spec and drifts
from it, so keep none. If an answer raises a new question, add it and ask it.

The step ends when every item is decided, or deliberately left open by the developer. When all are
decided, the Open items section reads `None.` Re-run the coverage check and both scripts from step 3
on the final spec before going on: a decision to drop a change can leave a product requirement with
no AC and no out-of-scope line, and renumbering leaves references pointing at the wrong item.

### 6. Approve (the one gate)

Show the developer the complete final spec in the conversation, in a message starting with
`[tech-spec-writer]` (see Rules), and state:

- the mode and the exact target (the ticket description / a new comment / a new sub-task under it,
  or the existing spec comment or sub-task you will update)
- any open items remaining
- every item settled by a blanket answer, each with the recommendation that was applied and where
  it now sits in the spec, so the developer sees what they accepted without reading it
- the coverage check: product requirements → ACs / out of scope

Wait for an explicit go-ahead. Nothing is written to Jira before it. With `--dry-run`, stop here.

### 7. Write to Jira

Use `contentFormat: "markdown"`. Write the spec in English, factually, without commenting on people
or teams.

**Marker.** Directly under the `# Technical Specification` heading, in every spec you write or
revise, put one line: `tech-spec-writer: <KEY> | product-rev <8 hex> | v<version> | <date>`. The
`product-rev` is `scripts/product_hash.py` run on the ticket's description plus all comments except
the spec's own, as read just before writing (so a change made during this run is caught next time);
`<version>` is the `version` in `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`. It is plain
visible text so no Jira editor strips it, and it is how the next run finds this spec and tells
whether the product text moved. A revised spec gets a new `product-rev` and date.

- **`update`** — `editJiraIssue` on the ticket's description. Under Background, add
  `### Original product requirements` with the product team's description quoted verbatim. Before
  writing, check whether the original holds content markdown cannot carry (images, panels,
  @mentions — `getJiraIssue` returns those bodies as HTML); if so, tell the developer at the gate
  that those elements are kept in the issue history rather than the new description.
  If the description is already a spec from an earlier run, replace it and keep the existing
  "Original product requirements" block as it is.
- **`comment`** — `addOrEditJiraIssueComment`. The comment starts with `# Technical Specification`.
  If an earlier spec comment exists (found by its marker, step 1), edit it rather than adding a second.
- **`create`** — `createJiraIssue` with the ticket's project, `issueTypeName: "Sub-task"`,
  `parent: <ticket>`, summary `[Tech Spec] <ticket summary>`, the spec as description, no assignee.
  If a `[Tech Spec]` sub-task exists, `editJiraIssue` that one instead.

### 8. Report

In English: the mode and where the spec now is (key and URL), the AC count, open items left (if
any), and the line the developer can paste into a fresh session to start implementing:

```
Read the Technical Specification on <KEY> and implement it on <branch>, plan step by step, red tests first.
```

## Rules

- **No ticket key → refuse.**
- **No code changes.** Read the repo; never edit, build, commit or transition. The one exception is the
  fallback project profile in `.claude/tech-spec-writer/` (step 2), and never on a dry run.
- **Ground "Current logic" in what you read** on the current branch and in its migration/data scripts, and say
  which branch, commit and date.
- **Every AC traces** to a product requirement, a rule or a code finding; every product requirement
  is covered or explicitly out of scope.
- **Decisions belong to the developer.** Recommend, but do not settle a real trade-off silently —
  make it an open item.
- **One gate** — explicit approval of the final spec before any Jira write. Automatic invocation
  does not skip it.
- **Idempotent** — a re-run revises the existing spec in place; it never files a second one.
- **English, unassigned, no editorialising.**
- **Prefix every pause with `[tech-spec-writer]`**: the first text of any message where the skill stops and waits (missing ticket key, auto-invocation confirmation, failed pre-flight or Jira call, each open item, the approval gate). With `AskUserQuestion`, put it at the start of the `question` text. The developer can then see which questions come from this skill.
