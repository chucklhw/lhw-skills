# Technical Specification: ACME-210 (example output)

> Illustrative output of `/tech-spec-writer ACME-210 --dry-run` on a fictional "Acme Shop" codebase.
> Class and script names are invented. Note how every claim in "Current logic" names its source, and
> how an unresolved decision is an **open item**, not a guess.

## Background

Merchants can only export all orders. This ticket adds a per-merchant list of statuses to export.
Constraint that matters most: **merchants who have not set the list must export exactly what they
do today.**

### Original product requirements

> Merchants currently get an export file for every order, including cancelled ones. They want to
> choose which statuses are exported. (ACs 1 to 4 as written on the ticket.)

## Rules

1. A merchant with no stored status list exports every order, as today (product AC 3).
2. The filter is applied in the export query, never after the file is built.
3. A status list is stored per merchant, in `merchant_setting`, not per store.
4. An empty list is invalid and is rejected on save, so it cannot silently export nothing.

## Current logic (verified in code and data scripts, `feature/export-filter` @ `a1b2c3d`, 2026-11-18)

* `NightlyExportJob.run()` calls `OrderExportMapper.selectOrdersForExport(merchantId, from, to)`.
  The query in `OrderExportMapper.xml` has no status condition today.
* `merchant_setting` already stores per-merchant key/value rows (created by
  `V31__create_merchant_setting.sql`). There is no key for export statuses yet.
* The Settings > Export screen (`ExportSettings.vue`) saves through `SettingsApi.save()`, which
  accepts any key. It does not validate values (see open item 1).

## Scope

**In scope:** the setting, the query filter, the Settings > Export control, tests.

**Out of scope:** exporting refunds as a separate file (sibling ticket); changing the file format.
Product's "refunded ones are probably the same" is not an AC, so it is not built (see open item 2).

## Acceptance Criteria

### AC1: Storage (rules 1, 3)

* A merchant's choice is one `merchant_setting` row, key `export.statuses`, value a comma-separated
  list. No row means "all statuses". No migration is needed, and no existing row is touched.

### AC2: Filtering (rules 1, 2; product AC 2)

* `selectOrdersForExport` adds `AND status IN (...)` only when the merchant has a stored list.
* An order whose status changes between two runs is exported according to its status at query time.

### AC3: Saving (rule 4; product AC 1, 4)

* Saving an empty list returns a validation error and stores nothing.
* The new value is read by the next nightly run, with no cache to clear.

### AC4: Tests

* Unit tests for the mapper with and without a stored list; a test that a merchant with no row
  exports the same orders as before; a UI test for the empty-list error.

## Spec / Implementation Plan

1. **Tests first (AC2, AC3).** Red tests in `OrderExportMapperTest` and `ExportSettingsTest`.
2. **Query (AC2).** Add the optional status condition to `selectOrdersForExport`.
3. **Setting read/write (AC1, AC3).** A small `ExportStatusSettingService` over `SettingsApi`.
4. **UI (AC3).** Status checkboxes in `ExportSettings.vue`.
5. **Verify.** Full suite, and a diff of an export for an untouched merchant before and after.

## Review Focus

1. **A merchant silently exporting nothing.** Guarded by rule 4 and AC3's validation.
2. **Changed behaviour for existing merchants.** Guarded by rule 1 and AC4's regression test.

## Open items

1. **Should the settings screen check the list itself, or should the server?**
   - Found: `SettingsApi.save()` stores any value for any key without checking it.
   - Options: (a) check on the server in the new service; (b) check only in the screen;
     (c) keep current behaviour, so nothing is checked.
   - Recommended: (a), because a check only in the screen can be skipped by any other caller.
   - Waiting on: developer.
2. **Should "refunded" orders be a separate choice from "cancelled"?**
   - Found: both exist as statuses in `OrderStatus`; the ticket only asks about cancelled ones.
   - Options: (a) list every status as its own tick box; (b) offer only "cancelled"; (c) keep
     current behaviour, so everything is exported.
   - Recommended: (a), because it needs no extra code and answers product's comment.
   - Waiting on: product team.
