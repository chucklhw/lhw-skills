## Error handling

| Channel | When | Notes |
| --- | --- | --- |
| Email to customer | Status changes | Recipient to follow the existing rule; proposal: the configured address, otherwise the connecting user **\[TO CONFIRM Q31\]** |

## Acceptance Criteria

| No | Given | When | Then |
| --- | --- | --- | --- |
| 9 | The token is invalid | The job runs | One email is sent **\[TO CONFIRM Q31: recipient\]** |
| 1 | A connection is stale **\[TO CONFIRM Q12: 3 days proposed\]** | The job runs | It is refreshed |
| 2 | Something **\[TO CONFIRM\]** | x | y |

## Open points

| Ref | Question | Who answers |
| --- | --- | --- |
| Q12 | Age threshold and exclusions | Tech lead, security owner |
| Q31 | Who is told about automated failures? See Q12 too. | PO - As in the other integration, automated user + tech support |
