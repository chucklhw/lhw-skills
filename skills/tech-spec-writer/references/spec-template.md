# Technical Specification template

The reference spec is **PD-11286** ("migrate myob alr config from app_config to integration_config").
When in doubt about tone or depth, read its description with `getJiraIssue` — it is the house style.
Excerpts below are from it.

Sections appear in exactly this order, in the draft and the final spec alike: Rules always comes
before Current logic. Headings are `##`; ACs are `###`. Omit a section only where noted, and add none
that is not listed here (no "Decisions" section: see Open items).

---

## Background

What the ticket is for, in technical terms, in a few sentences: the problem, the change, and the
constraint that matters most (e.g. "This is a migration: **business logic must not change**").
Name what this ticket builds on (another ticket's scripts, a branch) and what must run first.

Small tables are welcome where they make a list unambiguous:

> | Excluded key | Why it stays |
> | --- | --- |
> | `myob.accountrightlive.oauth.scopes` | Company-level: one value per company (PD-9348) |

In `update` mode, end Background with:

```markdown
### Original product requirements

> <the product team's description, verbatim>
```

## Rules

Numbered invariants the solution must keep — the "laws" of this change. Each is one or two
sentences, testable, and stated as a fact about the system after the change. ACs and Review Focus
cite them by number.

> 4. Values of migrated keys are read from `integration_config`.
> 5. Whether a value in `integration_config` is encrypted is decided by its own `encrypted` column,
>    never by `app_config_metadata` at read or write time.
> 7. The change goes through a new `IntegrationConfigService`. `ConfigService` is not touched, so
>    all other functionality is unaffected.

Developer decisions usually land here. Every rule is cited by at least one AC or Review Focus item.
Where a term has more than one meaning in the change (the connecting user vs the acting user, both
"user ID"), the rule names which one by role and field:

> 2. The **acting** user's ID on a refresh (`TokenRefreshRequest.userId`) never selects the token
>    and is only logged. The **connecting** user's ID is stored on the token row (rule 10).

## Current logic (verified in code and release SQL, `<branch>` @ `<short sha>`, `<YYYY-MM-DD>`)

What the code and data do **today**, only as far as you read and confirmed it. Name the class,
method, mapper statement or release script (`Version_8.783`, `sql/change/PD-9348_…`) behind each
point. Cover the data side — which rows exist, at which level, from which script — not just Java.

> * Today `ConfigServiceImpl.getIntegrationConfig(companyId, integrationId)` resolves a key in three
>   layers, each overriding the one before: global rows, company rows, integration rows.
> * `oauth.scopes` and `logging.enabled` exist **only** at company level, so they are excluded.
> * Among the migrated keys, **only** `…secret` and `…companyfile.password` have `encrypt = 1` (confirmed).

Where several names refer to one thing, map them here once ("company file name" = MYOB's
`businessName` on the redirect; the configured name is `myob.accountrightlive.entity`) and use one
term afterwards. A comment's or Javadoc's reason is stated only with what you confirmed in the code.

Confirm anything you inferred before writing it. If the code cannot confirm it, do not leave a
"(not confirmed)" note: raise an open item for the developer to confirm it and write "(see open
item n)" against the claim. End with the consequence for this ticket if it
is not obvious ("So that no existing integration loses a value it reads today, the migration
writes each integration's effective value…").

## <Topic section> (optional)

Only when one cross-cutting mechanism needs explaining once so the ACs can refer to it — PD-11286
has "Encryption". Do not add these for their own sake.

## Scope

**In scope:** bullet list of the pieces of work.

**Out of scope:** bullet list — sibling tickets ("the setup UI … (separate ticket)"), things that
stay as they are, and tempting adjacent improvements ("strengthening the encryption algorithm").
Every product requirement not covered by an AC appears here with the reason.

## Acceptance Criteria

Technical, not product, criteria: what a reviewer or a test can check in the code, the database or
the running system. One `###` per AC, titled by what it covers, citing rules and product
requirements where relevant.

> ### AC3: Reads (rule 4)
>
> * A migrated key is read from the integration's own live row in `integration_config`, by
>   `integration_id` and `config_key`. There is no company-level or global fallback (rule 8). An
>   absent row reads as blank.
> * A value written is visible to the very next read. There is no stale cache, because the OAuth
>   redirect writes a value and immediately restarts the export, which reads it back.

Good ACs state the condition precisely (columns, types, nullability, idempotency, what happens to
existing data), say what must **not** change, and give the reason when it is not obvious. Include
a **Tests** AC: JUnit 5 for new Java, `*SqlMapTest` for every new or edited mapper statement (the
SQL mapper gate requires it), Jest for Vue changes, updated tests for every switched class, and any
manual check on the feature server.

## Spec / Implementation Plan

Ordered work items, each referencing the ACs it delivers. Name the classes, interfaces, mapper
statements, SQL scripts and test classes involved, as found in the code — **no line numbers**, and
code only where a signature or DDL is itself the decision. Say how to find call sites that may move
("search the `AppConfig.MYOB_ACCOUNTRIGHTLIVE_*` constants and their call paths") rather than
listing lines that will drift. Keep the project's TDD order: tests red first.

> 4. **IntegrationConfigService (AC3–AC5).** A new interface in `prospend-lib-interface` and its
>    implementation in `prospend-lib-ems`. … Unit tests cover each behaviour.
> 6. **Verify (AC6, AC7).** Full test suite, the SQL mapper gate, a diff against the base branch for
>    the untouched areas, and the manual feature-server check.

Include SQL rehearsal steps where there are scripts (run, re-run, verify, roll back, re-apply on
`emsdev`), and release ordering where emsglobal or another ticket's scripts are involved.

## Review Focus

The specific ways this change could go wrong, most serious first, each ending with what guards it.

> 4. **A missed caller.** A place still reading a migrated key through `ConfigService` gets a blank
>    value after the migration. Guarded by AC6 and step 5's search.

## Open items

Decisions still needed, each as:

```markdown
1. **<Question>**
   - Found: <what the code/data shows, naming the class or script; a one-line snippet where it is the evidence>
   - Options: (a) … (b) … (c) keep current behaviour — <what that means>
   - Recommended: (<x>), because <reason>.
   - Waiting on: <developer / product team / …>
```

Every item has all four parts, including minor ones. For example:

> 2. **Who is recorded as the connecting user on a reconnect?**
>    - Found: `userId` is part of the table's DynamoDB sort key — `AccessTokenDynamoEntity.getSortKey()`
>      is `generateSortKey(dataType, userId, creationDate)`, so changing the user re-keys the row.
>    - Options: (a) new `connectedBy` / `connectedOn` attributes, key unchanged; (b) re-key the row on
>      each reconnect; (c) keep current behaviour — the connecting user is not recorded.
>    - Recommended: (a), because it records the user without touching the key every reader depends on.
>    - Waiting on: developer.

Resolved items do not stay here: each decision moves into Rules, Scope, an AC, a plan step or Review
Focus. When every item has been resolved that way, this section reads `None.` An item the developer
deliberately left open stays, with what it is waiting on. Open items is the last section: do not
follow it with a "Decisions" list or table, because each decision is already in the section it
moved to.
