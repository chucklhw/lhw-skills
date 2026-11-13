Thanks — here are my decisions on the open items:

1. Your most consequential open item: go with your recommendation.
2. Your least consequential open item: none of the options — I don't want any change there; keep the current behaviour.
3. For the expired-token / "Reconnection required" problem: I don't want to change the repository's `attribute_not_exists(expired)` filter. Instead, have the status check use `listAllIntegrationAccessTokens`, which I believe already reads without that filter, and treat the newest row being expired as "Reconnection required". Check that works.
4. For the rest, take your recommendation where it is low-risk. Anything whose recommendation changes what a customer sees or receives, adds stored data or a schema change, or departs from what the product team wrote or answered on the ticket: leave it open for me to decide explicitly.

Finish the spec and save it as tech-spec-final.md. Open items should keep only what I have not decided.
