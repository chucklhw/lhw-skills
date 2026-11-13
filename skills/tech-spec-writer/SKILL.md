---
name: tech-spec-writer
description: Turn a product-written Jira ticket (PD/SD) — its acceptance criteria, specs and comments — into a developer-approved Technical Specification grounded in the current branch's EMS source code and release SQL, then write it back to Jira by updating the description, adding a comment, or creating a "[Tech Spec]" sub-task. Works with the developer to resolve every implementation decision the code raises before anything is filed. Use whenever a developer asks to write, draft, generate or refine a tech spec, technical specification, technical ACs, implementation plan or solution design for a Jira ticket, or to "convert the product ACs" or "spec out" a ticket before coding — even if they don't say "technical specification". Refuses without a ticket key. Does not change code.
argument-hint: PD-XXXX | SD-XXXX [--mode comment|update|create] [--dry-run]
---

# tech-spec-writer

Converts what the product team wrote on a Jira ticket into a **Technical Specification** that a
later Claude session can implement from, and files it back to Jira. The flow is:

**read the ticket → read the code → draft → resolve open items with the developer → approve → write to Jira.**

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

1. `<ticket>` — **required**. A Jira key such as `PD-11286` or `SD-52579`.
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
2. **Authenticated and authorised**: call `getAccessibleAtlassianResources` and confirm that
   `expensemanager.atlassian.net` is in the result. An auth error, a server that is still waiting
   for authentication, or a list without that site all count as failure.

If either check fails, **stop and do not run the skill.** In a message starting with
`[tech-spec-writer]` (see Rules), tell the developer politely that the Jira
MCP is required. Say which check failed, and give them the short setup steps in
[references/mcp-setup.md](references/mcp-setup.md#jira-required), including how to set the Jira API
token. Do not offer to proceed from pasted ticket text instead: a spec built from a paste cannot
be filed or re-read by the implementing session.

**Figma MCP — optional.** Check whether Figma tools are in the session (a server named `figma`,
with tools such as `get_metadata`, `get_screenshot` or `get_design_context`, loaded or deferred)
and authorised (no "requires authentication" notice for it).

- **Available**: in step 1, use it to inspect every Figma link or design on the ticket, its
  comments and its parent epic. If a Figma skill in the session says it must be loaded before a
  tool you use, load it first. Treat what you find as product requirements, numbered with the
  rest, and cite the Figma node in the spec.
- **Not available or not authorised**: carry on as normal. Treat Figma links as sources you cannot
  read (step 1), and say once in the report that installing or authorising the Figma MCP would
  let the skill read them ([references/mcp-setup.md](references/mcp-setup.md#figma-optional)).

Tell the developer the result in one line before step 1, for example "Jira MCP: connected.
Figma MCP: not available, so Figma links will be listed as unread."

### 1. Read the ticket

`getJiraIssue` with `view: "evidence"`. PD/SD tickets live on `expensemanager.atlassian.net`
(cloudId `f75ea70e-92c7-45e7-ba34-d47a4dc23c52`); the wrong site is the usual reason the call fails.
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
  "proposal:" or "still open", look up that question everywhere before treating it as open: the
  Open points / questions table (including its "Who answers" or notes cell, where product owners
  often append the answer, e.g. "PO - As in Xero, Automated User + Tech Support"), dated decisions
  (D-31Oct), the comments, and the epic. Product teams answer a question in one place and leave the
  marker in others, so a marker alone does not mean the question is open. When an answer exists:
  - it is a product requirement: number it like any other (cite where it was answered) and build on it;
  - read it together with the proposal it answers (for example, the error-handling row's proposed
    recipient), and spell out what the answer means in this code; if the answer and the proposal
    differ, or the answer is too terse to apply, that difference is an open item for the developer,
    not for the product team;
  - note in Background, in one line, every place the marker still reads as open (for example "AC9
    still says TO CONFIRM Q31; answered in Open points"), so the product team can tidy the ticket.
  Only a question with no answer anywhere stays waiting on the product team (step 5).
  To find them mechanically, save the description (and comments) to a file in your scratch
  directory and run `python -I ${CLAUDE_PLUGIN_ROOT}/skills/tech-spec-writer/scripts/ticket_questions.py <file>`. It lists, per question id,
  every place marked TO CONFIRM, its open-points row and the "who answers" cell, flagging cells
  that hold more than role names as a possible answer. Read each flagged cell yourself: the flag
  means "look here", not "answered".
- **Figma designs** — with the Figma MCP available (step 0), open each linked design and add what
  it shows to the product requirements.
- **What you cannot read** — screenshots, attachments, and Figma links when the Figma MCP is not
  available. Say so plainly and list them as an open item if they hold a requirement you need.
- **An existing spec** — a description already in this format, a comment headed
  `# Technical Specification`, or a `[Tech Spec]` sub-task. If one exists, this run **revises** it
  rather than starting over: keep its decisions, re-verify its "Current logic", and change only
  what the code or the developer now says differently. Tell the developer you found it.

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
screen names, labels, field names, config keys, endpoints, ERP names, report names:

- **Frontend** — `prospend-adp-api/src/main/emsui/src/` (`v2/modules/` for newer code,
  `modules/` for legacy), `src/router.js`, the `*Api.js` the screen calls.
- **API** — controllers in `prospend-adp-api/src/main/java/com/prospend/web/api/`. Authorisation is
  usually in the Shiro filter chain in `prospend-adp-api/src/main/resources/global/spring-security-context.xml`,
  not in annotations — check it for any permission-related requirement.
- **Services and logic** — interfaces in `prospend-lib-interface`, implementations in
  `prospend-lib-impl`, `prospend-lib-ems` (`core/domain/logic/`) and `prospend-lib-logic`.
- **SQL** — mapper XML in `prospend-lib-sqlmap/src/main/resources/com/prospend/sqlmap/`;
  shared `<sql>` fragments and `<resultMap>`s reach other statements, so follow them.
- **Schema and data** — release scripts `sql/release/Version_8.*.sql` (older ones in
  `sql/release-archive/`), ticket scripts in `sql/change/`, emsglobal metadata in
  `sql/app_config_metadata.sql`. Data the code depends on (config rows, metadata tags, seed rows)
  is part of "current logic" just as much as Java is.
- **Tests** — the existing tests for each class you will change, so the plan can say which must be
  updated.

Search with `python -I ${CLAUDE_PLUGIN_ROOT}/skills/tech-spec-writer/scripts/search.py <pattern> --repo <repo> [--path <dir>] [--glob '*.java']
[-w] [-F] [-l]` rather than `grep -r`. It searches tracked files only (never `node_modules` or build
output), cuts long lines and caps the output, telling you how many matches it did not show; narrow
with `--path`/`--glob` instead of raising `--max`. An unscoped `grep -r` of `prospend-adp-api/src`
walks `node_modules` and returns megabytes.

Read the code until you can explain, for each requirement, **what happens today and why**. Keep a
map of concern → class/statement/script. This is the most valuable thing you produce: product ACs
describe intent, and almost every real decision in a spec comes from something the code does that
the product team did not know about — a second caller, a layered lookup, a company-level fallback,
encrypted values, a cache, a sibling feature sharing the same table.

Mind the domain gotchas in `CLAUDE.md` (for example: `Expense.currencyCode` is the currency of
`foreignAmount`, not `amount`). A spec that repeats a known wrong assumption sends the next session
straight into a known bug.

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

### 3. Draft the spec

Write the draft in the structure in `references/spec-template.md` — read that file now; it
explains what each section is for and shows examples from PD-11286, the reference spec. Use exactly
these sections, in exactly this order, in every version of the spec (draft and final). In
particular, Rules comes before Current logic. Add no other `##` sections, and in particular no
"Decisions" or "Decisions taken" section (see step 5). In short:

1. **Background** — the problem, in technical terms, and the original product text (quoted in
   `update` mode).
2. **Rules** — numbered invariants the solution must keep. ACs cite them.
3. **Current logic (verified in code and release SQL, `<branch>` @ `<sha>`, `<date>`)** — what the
   code and data do today, only what you read and confirmed.
4. **Topic sections** — only when the ticket needs one (PD-11286 has "Encryption").
5. **Scope** — in scope / out of scope, explicit.
6. **Acceptance Criteria** — technical, numbered `AC1…`, each verifiable, each citing its rules.
7. **Spec / Implementation Plan** — ordered work items naming the classes, statements, scripts and
   tests involved, no line numbers.
8. **Review Focus** — the ways this change could go wrong, each ending "Guarded by …".
9. **Open items** — decisions still needed.

Write plainly and precisely. Every statement in "Current logic" must be something you read in the
code or SQL. **Nothing stays "not confirmed".** When you find yourself inferring something, first
try to confirm it: read the class, follow the call, search the SQL. If it is confirmed, state it
with its evidence. If it cannot be confirmed from the code (it depends on deployed configuration,
live data, another repository or MYOB behaviour), make it an open item for the developer to
confirm, saying what you checked, what is still unknown and how they could check it. Then point
to that item from the claim ("see open item 3"). This applies to every section, not only
"Current logic": a rule, AC, plan step or Review Focus item may not rest on an unconfirmed claim
either. Every technical AC
must trace to a product requirement (`P1…`), a rule, or something you found in the code. Do not
invent requirements; if the code suggests something the product team did not ask for, it is an
open item, not an AC.

**Show evidence where a reader would otherwise have to take your word for it.** The developer
deciding an open item, and the reviewer approving the spec, need to see *why* you believe a
finding — especially a surprising one, or one an AC or decision rests on. Point at where it lives,
and when the exact expression is the point, quote the few characters that prove it:

> Found: `AccessToken.userId` is part of the table's DynamoDB sort key —
> `AccessTokenDynamoEntity.getSortKey()` is `generateSortKey(dataType, userId, creationDate)`.

Quote the line that proves *this* claim. A similar-looking line nearby (here,
`generateIntegrationSortKey`, which has no `userId`) proves something else, and a reviewer who opens
the file will notice.

> Found: the PD-9348 script seeds `myob.accountrightlive.oauth.scopes = LEGACY` (`sql/change/`).

Balance this against readability. Most statements need only the class or script name; a snippet
earns its place only when it settles a question a reader would otherwise have to open the file to
answer. Keep snippets to one line or one short expression — a quoted method body is a sign you are
explaining code rather than specifying a change.

**Name which one you mean when a term has more than one meaning in this change.** A domain often
uses one word for several things: "user ID" can be the user who connected, the user who triggered
an action, or the `userId` key attribute; "status" can be a stored column or a derived value;
"integration" can be the row or the ERP connection. When the spec uses such a term in more than one
sense, every rule, AC and plan step that mentions it says which one, by role and by field
(`TokenRefreshRequest.userId`, the acting user) — and where two senses sit close together, it
points at the other ("the connecting user's ID is stored on the token row, rule 10"). An implementer
reads a rule on its own; "a user ID passed in is used for logging only" next to "store the user ID"
reads as a contradiction even when both are right.

The reverse happens too: **two terms for one thing.** The product says "company file name", MYOB's
redirect says `businessName`, the setting is `myob.accountrightlive.entity` labelled "Company File
Name". When you find this, state the mapping once (in Background or Current logic, a small table is
fine), say whether the values are really the same or only describe the same thing from different
sources (an admin-typed setting vs the value MYOB returns), and use one term from then on.

**Trace every person or role the ticket names to a code identity.** Tickets name people by role:
"the connecting Administrator", "the sync user", "the automated user", "the approver". Each one
becomes a recipient, a permission or a stored value in the solution, so treat the role as an
assumption until the code backs it. For each, find and state with evidence:

- **Which identity in the code it is**: a ProSpend login (`Login`, `userId`), a user in the ERP
  (a MYOB company file Administrator), a system or run-as login, the user on a queued action, or a
  configured address.
- **Where that identity is captured**: the endpoint or job where it first appears, for example the
  current login when `api/accountrightlive/login` starts consent.
- **Who can actually be it**: the roles that can reach that entry point (the Shiro filter chain in
  `spring-security-context.xml`, `@RequiresRoles`). The ticket says "Administrator"; the code may also let
  a payer or a ProSpend support user through.
- **Whether it is stored, and where**: or only passed through and dropped (for example, in a context
  object that is never written).
- **Whether two identities are assumed to be one**: the ProSpend user who clicks Connect and the
  MYOB Administrator who signs in at MYOB are different accounts, and only one may be visible to
  ProSpend.

Anything the code settles, state as a fact in Current logic. Anything it cannot settle (the
ticket's role is narrower than the roles the code admits, the identity is not stored, or the
mapping between two identities is assumed) is an open item for the developer.

**Comments and Javadoc are claims, not evidence.** When one explains why the code does something
("deliberately not persisted because…"), check the reason against the code paths it describes
before relying on it — follow the call, look at the branch conditions. Quote the comment only
together with what you confirmed, and if the code disagrees (for example, the check it protects is
only reached on a first connect), say so in Current logic.

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

- the product AC conflicts with existing behaviour, or would break another feature sharing the code
  — including logic the code chose on purpose (e.g. the product asks to store the consented company
  file name; the code deliberately stores only the id, and the name is compared by a guard and used
  by the legacy company file lookup). Show the conflicting line and let the developer decide.
- more than one place implements the same rule (FE and BE, two services, two mappers)
- existing data would not satisfy the new rule — a migration, backfill or default is needed
- a requirement is silent on an edge case the code must handle (empty, null, deleted, multi-currency,
  multi-company, permissions, existing records)
- a choice of approach with real trade-offs (new service vs extending one, schema change vs config)
- release ordering, feature flags, or tenant-wide (emsglobal) data
- something you could not read or find

For each, write: **the question**, **what you found** (with the class/script, and a snippet where it
is the evidence), **the options**, and **your recommendation with the reason**. All four, for every
item — including the minor ones and the ones about something you could not read. A recommendation
without a reason ("Recommended: (a).") gives the developer nothing to weigh, and is the most common
way these items fall short. For an unreadable source (a Figma link without the Figma MCP, a design
ticket you could not open), the options are what the spec would do under each plausible reading, and the recommendation
may be "ask the product team before deciding" — with the reason.

Make clear what **leaving things as they are** would mean, as one of the options where it is a
realistic choice: the developer may decide the change is not wanted at all.

Do not file trivia — if the code and the product text together leave only one sensible answer,
decide it and state it in the spec.

### 5. Resolve the open items with the developer

The developer owns the solution; your job is to put each decision in front of them with the evidence,
and then make the spec say exactly what they decided. This is a conversation, not a form.

Present the draft's shape briefly (sections and AC titles), then ask about the open items **one at
a time, most consequential first** — `AskUserQuestion` when the options are discrete, plain
conversation when they are not. Ask the question, give the finding and the options, and say which
you recommend and why. Answers that settle an earlier item often change a later one, which is why
they go one at a time.

Ask strictly one item per message and wait for the answer before asking the next. Never batch
several open items into one message or one `AskUserQuestion` call. Start each with the
`[tech-spec-writer]` prefix (see Rules), for example:

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
- **Asks you to look further.** Do it, report what you found, and re-ask.
- **Wants to leave it open** (for example, waiting on the product team). It stays in Open items with
  who or what it is waiting on — the only way an item survives this step.
- **Answers an item that is waiting on someone else.** If an item (or part of one) is waiting on the
  product team or anyone other than the developer, a blanket answer such as "take your
  recommendation for everything else" does not settle it, because the developer cannot answer for
  them. Settle only the part the developer owns. The waiting part stays in Open items, worded as
  the open question with "Waiting on: product team" (or whoever), and no Rule, Scope line or AC may
  decide it in the meantime, for example by declaring it not implemented. It leaves Open items only
  when the developer passes on that party's answer or explicitly says to go ahead without it, and
  then the spec says so.
- **Gives a blanket answer** ("take your recommendation for the rest", "whatever you think"). It
  settles only low-impact items. An item needs the developer's explicit answer, and stays in Open
  items marked "Waiting on: developer (explicit decision needed; not settled by a blanket answer)",
  when its recommendation:
  - departs from what the product team wrote or answered on the ticket (for example, a different
    email recipient from the one in the product owner's answer);
  - changes what a customer sees or receives (screens, emails, exports, error messages);
  - adds stored data or a schema change (a new column, attribute, config key or SQL script); or
  - was raised by the skill's own risk checks (a conflict between an AC and the code, a security or
    data-loss concern, or a role the code cannot map).

  Ask about each such item in its own message, as above, before showing the final spec. Never apply
  a blanket answer to them silently.

After each decision, **update the spec, not just the list**: the decision becomes a rule, an AC, a
scope line, a plan step or a Review Focus item, and the item leaves Open items. Then check what it
touches elsewhere — an AC that assumed another option, a plan step now unnecessary, a risk that no
longer applies — and fix those too. Before adding a rule, look for an existing rule on the same
subject. If one exists, merge the decision into it: one rule that keeps every detail of both (each
condition, value, exception and citation), so that nothing in either version is lost. Do not add a
near-duplicate, and do not simply overwrite the old rule. If two existing rules already overlap,
merge them the same way into the earlier one, remove the later one, and update every AC, plan step
and Review Focus item that cited a rule number that changed. A decision recorded only in the chat is lost to the session that
implements the spec. Do not also keep a log of decisions: no "Decisions" section, table or
subsection. The section where each decision now lives is the only record of it, and a separate
list repeats the spec and drifts from it. If an answer raises a new question, add it and ask it.

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

- **`update`** — `editJiraIssue` on the ticket's description. Under Background, add
  `### Original product requirements` with the product team's description quoted verbatim. Before
  writing, check whether the original holds content markdown cannot carry (images, panels,
  @mentions — `getJiraIssue` returns those bodies as HTML); if so, tell the developer at the gate
  that those elements are kept in the issue history rather than the new description.
  If the description is already a spec from an earlier run, replace it and keep the existing
  "Original product requirements" block as it is.
- **`comment`** — `addOrEditJiraIssueComment`. The comment starts with `# Technical Specification`.
  If an earlier spec comment exists, edit it rather than adding a second.
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
- **No code changes.** Read the repo; never edit, build, commit or transition.
- **Ground "Current logic" in what you read** on the current branch and in the release SQL, and say
  which branch, commit and date.
- **Every AC traces** to a product requirement, a rule or a code finding; every product requirement
  is covered or explicitly out of scope.
- **Decisions belong to the developer.** Recommend, but do not settle a real trade-off silently —
  make it an open item.
- **One gate** — explicit approval of the final spec before any Jira write. Automatic invocation
  does not skip it.
- **Idempotent** — a re-run revises the existing spec in place; it never files a second one.
- **English, unassigned, no editorialising.**
- **Prefix every pause with `[tech-spec-writer]`.** Whenever the skill stops and waits for the
  developer, start that message with `[tech-spec-writer]` as its first text, on its own line or at
  the very beginning of the first sentence. With `AskUserQuestion`, put it at the start of the
  `question` text. This covers asking for a missing ticket key, confirming the ticket key and mode
  on automatic invocation, a failed Jira pre-flight check (step 0) or Jira call, each open item
  (step 5) and the approval gate (step 6). It lets the developer see at a glance which questions
  come from this skill.

## Common mistakes

| Mistake | What to do instead |
| --- | --- |
| Rewriting the product ACs in technical words and calling it a spec | The value is in what the code shows. Read it first; most ACs and every open item come from there. |
| "Current logic" that describes what the code *probably* does | Only what you read. Name the class or script. Confirm anything inferred in the code; if the code cannot confirm it, raise it as an open item for the developer. |
| Line numbers and full code in the plan | They go stale before the work starts. Name classes, statements and scripts; give DDL or a signature only when it *is* the decision. |
| Deciding a trade-off yourself because one option looked better | Put it in Open items with your recommendation. The developer owns the solution. |
| Recording a decision only in the chat | Fold it into Rules / ACs / Scope / Plan, then remove it from Open items. |
| Missing the data side of the change | Config rows, metadata tags, existing records and release order are part of the solution. Check `sql/`. |
| Writing to Jira after the developer answered the last open item | Answering items is not approval. Show the final spec and ask. |
| Writing in the developer's own proposal without checking it | Evaluate it against the code like any option, tell them what you found, then apply what they decide. |
| A rule that says "the user ID" (or "status", "token"…) when the spec uses that term in two senses | Say which one — by role and field — and point at the other sense where they sit close together. |
| Two names for one thing ("company file name", `businessName`, `entity`) used interchangeably | Map them once, say where each value comes from, then use one term. |
| Reading "as in <X>" or "same as PD-nnnn" as a description rather than a pointer | Find and read the code that implements the reference, state what it does, and offer copying it as an option. |
| Assuming a role in the ticket is a user the code knows ("email the connecting Administrator" → store the connecting `userId`) | Trace it: who the code captures, which roles can reach that point (payer and support may connect too), whether it is stored, and whether the ProSpend user is the MYOB Administrator. Raise what the code cannot settle as an open item. |
| Repeating a comment's or Javadoc's reason as fact | Check the reason against the code paths; report it only with what you confirmed. |
| Marking a product requirement "met" or "kept" when the code deliberately does something else | It is a conflict: open item with the conflicting line, options and a recommendation. |
| A "keep as is" rule that no AC or Review Focus item cites | Give it a check: an AC line, a Tests item or a Review Focus entry, so the implementer verifies it. |
| Treating "none of these" as no answer | It is a decision to keep things as they are. Record it as scope or a rule and remove what assumed the change. |
