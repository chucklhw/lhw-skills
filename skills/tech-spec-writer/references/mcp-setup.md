# MCP setup

Give the developer only the section they need, in a few lines. Product menus and endpoints change,
so tell them to check the vendor's current documentation if a step does not match what they see.

## Jira (required)

ProSpend tickets are on `expensemanager.atlassian.net`. Either option works.

**Option A: Atlassian connector (OAuth).**
1. Claude desktop app: **Settings → Connectors**, add **Atlassian**, then sign in with the
   ProSpend Atlassian account. Claude Code CLI: run `/mcp`, choose the Atlassian server and
   authenticate.
2. Approve access to `expensemanager.atlassian.net`.

**Option B: Jira API token.**
1. Create a token at <https://id.atlassian.com/manage-profile/security/api-tokens>
   ("Create API token"). Copy it at once, because it is shown only once.
2. Configure a Jira MCP server that accepts a token, with:
   - site URL: `https://expensemanager.atlassian.net`
   - username: your Atlassian account email
   - API token: the token from step 1

   For example, the open-source `mcp-atlassian` server reads `JIRA_URL`, `JIRA_USERNAME` and
   `JIRA_API_TOKEN` from its environment.
3. Keep the token out of any file that is committed. Put it in user-level config or an environment
   variable, never in the repository.

Then restart the session (or reconnect the server) and run the skill again.

## Figma (optional)

Without it, the skill lists Figma links as sources it could not read.

1. Claude desktop app: **Settings → Connectors**, add **Figma** and sign in. Claude Code CLI:
   install the Figma plugin or MCP server, then run `/mcp` and authenticate.
2. Make sure the Figma account can view the files linked from the ticket.
