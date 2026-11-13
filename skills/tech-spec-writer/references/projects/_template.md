---
name: <project-slug>
detect-paths: [<a path that exists only in this repository, e.g. a top-level module>]
jira-site: <your-site>.atlassian.net
jira-cloud-id: <cloudId, from getAccessibleAtlassianResources>
jira-project-keys: [<KEY>]
---

# Project profile: <Project name>

Project-specific knowledge for `tech-spec-writer`. SKILL.md holds the generic method; this file
holds what is true only of this repository. It is a starting map, not evidence: confirm against the
code on the current branch, and correct this file when the repository has moved on.

Record only what you read or the developer told you. Leave a section out rather than guess. Never
write credentials, tokens or customer data here.

## Jira
Site, cloudId and project keys (also in the front matter). Anything that explains common call failures.

## Code map
Where each concern lives: frontend, API/controllers, services/logic, data access, schema and
migrations, config, tests. Real paths, one line each.
Include how to scope searches (directories that are huge or generated, to skip).

## Authorisation and identity
Where permissions are enforced (annotations, a filter chain, middleware, config) and the roles that
exist. Which identities the system knows (login, service account, queued-action user).

## Tests and conventions
Test frameworks and naming, required gates (for example mapper or contract tests), TDD or review
rules, how to run the suite.

## Release and data
Migration/release script locations and ordering rules, feature flags, environments to rehearse on,
tenant-wide or global data.

## Domain gotchas
Known wrong assumptions, units, naming traps, and where the repository documents them (for example
`CLAUDE.md` or `README`).

## Terminology
Terms the product and the code use differently, mapped once.

## Worked examples (optional)
One or two short excerpts from a good spec for this project (a rule, an AC, an open item), so the
house style is easy to match.
