# lhw-skills

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Claude Code skills for developers. Currently one skill: **`tech-spec-writer`**.

## tech-spec-writer: from a Jira ticket to a spec your team can approve

Product writes acceptance criteria. Developers then spend an hour reading code to find out what they
really mean. `tech-spec-writer` does that reading for you:

- Reads the ticket (acceptance criteria, specs, comments) and the code and data scripts **on your current branch**.
- Drafts a Technical Specification where every claim about today's behaviour names the class, query or script it came from.
- Raises each real implementation decision as a plain-English **open item** with options and a recommendation, instead of guessing.
- Writes the approved spec back to Jira as a description update, a comment or a "[Tech Spec]" sub-task. Nothing is written until you approve.
- On a re-run, finds the earlier spec and revises only what changed acceptance criteria affect.
- Never changes your code.

See a full example of the output, on a fictional ticket, in [`examples/acme-shop-demo`](examples/acme-shop-demo/).
It ships with [evaluation cases](skills/tech-spec-writer/evals/) so changes to the skill can be tested.

### Quick start

```bash
git clone https://github.com/chucklhw/lhw-skills.git
cd /path/to/your/repo            # the repository the ticket is about
claude --plugin-dir /path/to/lhw-skills
```

Then, in Claude Code, try it without touching Jira:

```
/tech-spec-writer PROJ-1234 --dry-run
```

You need Claude Code, Python 3, `git` and a Jira connection (setup in
[`mcp-setup.md`](skills/tech-spec-writer/references/mcp-setup.md)). It works with any repository.

## Installation

Run `/help` or type `/tech-spec-writer` to confirm the skill is listed (it may appear namespaced as
`lhw-skills:tech-spec-writer`). To install it persistently, add the repository as a plugin
marketplace or install it from a Git URL using `/plugin` (see the Claude Code plugin documentation
for the current syntax).

### Requirements

- Claude Code
- Python 3 and `git` on `PATH` (the helper scripts use only the standard library;
  see `requirements.txt`, which lists no third-party packages)
- A local checkout of the repository the ticket is about, on the branch you want the spec grounded in
- A Jira connection (required) and Figma (optional) — see
  `skills/tech-spec-writer/references/mcp-setup.md`

## Using tech-spec-writer

Open Claude Code **inside the repository the ticket is about** (the skill reads the current branch) and run:

```
/tech-spec-writer PROJ-1234
/tech-spec-writer PROJ-1234 --mode comment
/tech-spec-writer PROJ-1234 --mode create --dry-run
```

Arguments:

- `<JIRA-KEY>` — the Jira ticket key, for example `PROJ-1234`. Required; the skill refuses without it.
- `--mode comment|update|create` — how to write the result back: add a comment, update the
  description, or create a "[Tech Spec]" sub-task.
- `--dry-run` — draft and review the spec without writing anything to Jira.

Workflow, in brief:

1. Checks the Jira (and optional Figma) tools are connected, then loads the matching project
   profile (see below) if there is one.
2. Reads the ticket: acceptance criteria, specs and comments.
3. Reads the relevant code and data/migration scripts on the current branch, and creates a project
   profile if the project has none yet.
4. Drafts the spec using `references/spec-template.md`.
5. Works through each open implementation decision with you.
6. You approve once; only then is anything written to Jira.

The skill does not change code, run builds, commit, or transition the ticket.

## Project profiles

The skill is generic. What is specific to one repository (where code, auth, tests and release
scripts live, domain gotchas, Jira site) goes in `skills/tech-spec-writer/references/projects/<project>.md`.

- On each run the skill matches the current repository to a profile by the `detect-paths` or `name`
  in the profile's front matter. Profiles are generated and updated by the skill at run time on each machine,
  so the author's own profile is git-ignored.
- With no match, the skill creates `<repo-folder>.md` from `_template.md` after reading the code and
  tells you. On every later run it updates, changes or overwrites the profile to match the ticket and
  branch it just verified (they may differ each time), so it stays up to date and small (about 120
  lines). It never records customer data or credentials.
- Profiles are written into the skill's `references/projects/`. If you cannot write there (a read-only
  or managed plugin install), the skill writes `<project>.md` into your repository's
  `.claude/tech-spec-writer/` instead, tells you it is a new untracked file, and leaves committing or
  excluding it to you. It never writes into the repository on a `--dry-run`; it prints the profile in
  the conversation instead.
- A plugin re-install may replace the skill's directory. Profiles other than `ems.md` are not
  git-ignored, so commit them if you want to share them.

## Repository layout

```
.claude-plugin/plugin.json     Plugin manifest
requirements.txt               Python dependencies (none beyond the standard library)
skills/
  tech-spec-writer/
    SKILL.md                   Skill instructions
    references/                Spec template and MCP setup notes
      projects/                Per-project profiles (_template.md, one per project)
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

## Contributing and licence

Issues and ideas are welcome. Released under the [MIT licence](LICENSE). See the
[changelog](CHANGELOG.md) for release history.
