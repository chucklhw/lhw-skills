# lhw-skills

A Claude Code plugin containing personal skills by chucklhw.

## Skills

| Skill | Purpose |
|-------|---------|
| `tech-spec-writer` | Turns a product-written Jira ticket (PD/SD) into a developer-approved Technical Specification grounded in the current branch's EMS source code and release SQL, then writes it back to Jira. |

## Installation

Clone the repository and load it as a plugin for a session:

```bash
git clone <repository-url> lhw-skills
claude --plugin-dir ./lhw-skills
```

To install it persistently, add the repository as a plugin marketplace or install it from a Git
URL using `/plugin` (see the Claude Code plugin documentation for the current syntax).

Run `/help` or type `/tech-spec-writer` to confirm the skill is listed (it may appear namespaced as
`lhw-skills:tech-spec-writer`).

### Requirements

- Claude Code
- Python 3 and `git` on `PATH` (the helper scripts use only the standard library;
  see `requirements.txt`, which lists no third-party packages)
- A local checkout of the EMS repository, on the branch you want the spec grounded in
- A Jira connection (required) and Figma (optional) — see
  `skills/tech-spec-writer/references/mcp-setup.md`

## Using tech-spec-writer

Open Claude Code **inside the EMS repository** (the skill reads the current branch) and run:

```
/tech-spec-writer PD-1234
/tech-spec-writer SD-1234 --mode comment
/tech-spec-writer PD-1234 --mode create --dry-run
```

Arguments:

- `PD-XXXX | SD-XXXX` — the Jira ticket key. Required; the skill refuses without it.
- `--mode comment|update|create` — how to write the result back: add a comment, update the
  description, or create a "[Tech Spec]" sub-task.
- `--dry-run` — draft and review the spec without writing anything to Jira.

Workflow, in brief:

1. Checks the Jira (and optional Figma) tools are connected.
2. Reads the ticket: acceptance criteria, specs and comments.
3. Reads the relevant code and release SQL on the current branch.
4. Drafts the spec using `references/spec-template.md`.
5. Works through each open implementation decision with you.
6. You approve once; only then is anything written to Jira.

The skill does not change code, run builds, commit, or transition the ticket.

## Repository layout

```
.claude-plugin/plugin.json     Plugin manifest
requirements.txt               Python dependencies (none beyond the standard library)
skills/
  tech-spec-writer/
    SKILL.md                   Skill instructions
    references/                Spec template and MCP setup notes
    scripts/                   Read-only helper scripts (+ tests)
    evals/                     Evaluation cases
```

Scripts in `SKILL.md` are referenced as `${CLAUDE_PLUGIN_ROOT}/skills/tech-spec-writer/scripts/...`
so they resolve wherever the plugin is installed.

## Development

Run the script tests:

```bash
python -m unittest discover -s skills/tech-spec-writer/scripts/tests
```
