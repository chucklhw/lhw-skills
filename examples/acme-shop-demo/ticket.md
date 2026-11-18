# ACME-210: Let merchants choose which order statuses trigger the export

> Fictional example ticket, written for this demo. "Acme Shop" is not a real product.

**Type:** Story  **Reporter:** Product  **Status:** Ready for dev

## Description

Merchants currently get an export file for every order, including cancelled ones. They want to
choose which statuses are exported.

## Acceptance Criteria (product)

1. In Settings > Export, a merchant can tick one or more order statuses to export.
2. Only orders in a ticked status appear in the nightly export.
3. Existing merchants keep exporting everything until they change the setting.
4. Changes take effect from the next nightly export.

## Comments

- **Product:** Cancelled orders are the main complaint. Refunded ones are probably the same.
