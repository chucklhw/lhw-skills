"""Check a tech-spec markdown file against the structure in references/spec-template.md.

Usage: python -I check_spec.py <spec.md> [--repo <path>]

Prints one line per problem ("<line>: <problem>") and exits 1, or prints "OK" and exits 0.
With --repo, also checks that the Current logic heading names the repository's current branch
and short commit. Reads files only; changes nothing.
"""
import argparse
import re
import subprocess
import sys

REQUIRED = ["Background", "Rules", "Current logic", "Scope", "Acceptance Criteria",
            "Spec / Implementation Plan", "Review Focus", "Open items"]
OPEN_ITEM_PARTS = ["Found:", "Options:", "Recommended:", "Waiting on:"]
# A reference preceded by another ticket's key ("PD-11009 AC16") or by "product" ("product AC9")
# points at the ticket's own criteria, not this spec's.
OTHER_TICKET = re.compile(r"(?:[A-Z][A-Z0-9]+-\d+(?:'s)?|\b[Pp]roduct|\bticket's)\s*$")
NUM_LIST = r"\d+(?:\s*[-–]\s*\d+)?(?:\s*(?:,|and|&|or)\s*\d+(?:\s*[-–]\s*\d+)?)*"
RULE_REF = re.compile(r"\b[Rr]ules?\s+(" + NUM_LIST + r")")
AC_REF = re.compile(r"\bACs?\s*(" + NUM_LIST + r")")
OPEN_REF = re.compile(r"\b[Oo]pen items?\s+(" + NUM_LIST + r")")
LINE_NUMBER = re.compile(r"\.(?:java|xml|sql|vue|js|ts|py):\d+|\b[Ll]ines?\s+\d+|#L\d+")


def numbers(text):
    """Expands "1, 3-5 and 7" to {1, 3, 4, 5, 7}."""
    result = set()
    for a, b in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", text):
        result.update(range(int(a), int(b or a) + 1))
    return result


def split_sections(lines):
    """Returns [(title, start_line, end_line)] for each ## heading (1-based, end exclusive)."""
    heads = [(i, l[3:].strip()) for i, l in enumerate(lines) if l.startswith("## ")]
    return [(t, i + 1, (heads[n + 1][0] if n + 1 < len(heads) else len(lines)) + 1)
            for n, (i, t) in enumerate(heads)]


def canonical(title):
    for name in REQUIRED:
        if title == name or title.startswith(name + " ") or title.startswith(name + "("):
            return name
    return None


def top_items(lines, start, end):
    """Top-level numbered items ("1. ...") of a section, as [(number, first_line, text)]."""
    items, current = [], None
    for i in range(start, end - 1):
        m = re.match(r"(\d+)\.\s", lines[i])
        if m:
            current = [int(m.group(1)), i + 1, lines[i]]
            items.append(current)
        elif current is not None and lines[i].strip():
            current[2] += "\n" + lines[i]
    return [tuple(x) for x in items]


def refs(regex, text):
    for m in regex.finditer(text):
        if not OTHER_TICKET.search(text[:m.start()]):
            yield m


def check(path, repo=None):
    lines = open(path, encoding="utf-8").read().split("\n")
    problems = []

    def add(line, msg):
        problems.append((line, msg))

    sections = split_sections(lines)
    by_name = {}
    order = []
    for title, start, end in sections:
        name = canonical(title)
        if "decision" in title.lower():
            add(start, f'section "{title}" is not in the template; fold decisions into the spec')
        elif name is None:
            order.append(("topic", start, title))
        else:
            if name in by_name:
                add(start, f'section "{name}" appears twice')
            by_name[name] = (start, end)
            order.append((name, start, title))
    for name in REQUIRED:
        if name not in by_name:
            add(0, f'missing section "{name}"')
    seen = [n for n, _, _ in order if n != "topic"]
    expected = [n for n in REQUIRED if n in seen]
    if seen != expected:
        add(0, "sections out of order: " + " > ".join(seen) + "; expected " + " > ".join(expected))
    # Topic sections may only sit between Current logic and Scope.
    for idx, (n, start, title) in enumerate(order):
        if n == "topic" and "decision" not in title.lower():
            before = [o[0] for o in order[:idx] if o[0] != "topic"]
            after = [o[0] for o in order[idx + 1:] if o[0] != "topic"]
            if not before or before[-1] != "Current logic" or (after and after[0] != "Scope"):
                add(start, f'section "{title}" is not in the template (topic sections go between Current logic and Scope)')
    def body(name):
        if name not in by_name:
            return ""
        s, e = by_name[name]
        return "\n".join(lines[s:e - 1])

    # Current logic heading carries branch, commit and date.
    if "Current logic" in by_name:
        s = by_name["Current logic"][0]
        head = lines[s - 1]
        m = re.search(r"`([^`]+)`\s*@\s*`([0-9a-f]{7,40})`.*?(\d{4}-\d{2}-\d{2})", head)
        if not m:
            add(s, "Current logic heading must name `<branch>` @ `<short sha>` and a YYYY-MM-DD date")
        elif repo:
            git = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True).stdout.strip()
            branch, sha = git("rev-parse", "--abbrev-ref", "HEAD"), git("rev-parse", "HEAD")
            if m.group(1) != branch:
                add(s, f"Current logic names branch {m.group(1)}, but the repository is on {branch}")
            if not sha.startswith(m.group(2)):
                add(s, f"Current logic names commit {m.group(2)}, but HEAD is {sha[:10]}")

    # Rules: numbered and each cited by an AC or Review Focus item.
    rules = top_items(lines, *by_name["Rules"]) if "Rules" in by_name else []
    rule_nums = {n for n, _, _ in rules}
    if "Rules" in by_name and not rules:
        add(by_name["Rules"][0], "Rules has no numbered rules")
    cited = set()
    for name in ("Acceptance Criteria", "Review Focus"):
        for m in refs(RULE_REF, body(name)):
            cited |= numbers(m.group(1))
    for n, line, _ in rules:
        if n not in cited:
            add(line, f"rule {n} is not cited by any AC or Review Focus item")

    # ACs are ### ACn headings.
    ac_nums = set()
    if "Acceptance Criteria" in by_name:
        s, e = by_name["Acceptance Criteria"]
        for i in range(s, e - 1):
            m = re.match(r"###\s+AC(\d+)\b", lines[i])
            if m:
                ac_nums.add(int(m.group(1)))
        if not ac_nums:
            add(s, "Acceptance Criteria has no '### ACn' headings")
        if not re.search(r"(?i)\btests?\b", body("Acceptance Criteria")):
            add(s, "no AC defines the tests")

    # Open items: four parts each, or "None."
    open_nums = set()
    if "Open items" in by_name:
        s, e = by_name["Open items"]
        items = top_items(lines, s, e)
        text = body("Open items").strip()
        if not items and text not in ("None.", "None"):
            add(s, 'Open items must list numbered items or read "None."')
        for n, line, item in items:
            open_nums.add(n)
            missing = [p for p in OPEN_ITEM_PARTS if p not in item]
            if missing:
                add(line, f"open item {n} lacks: " + ", ".join(missing))

    # Review Focus items each name their guard.
    if "Review Focus" in by_name:
        for n, line, item in top_items(lines, *by_name["Review Focus"]):
            if "guarded by" not in item.lower():
                add(line, f'Review Focus item {n} does not say "Guarded by"')

    # References must point at things that exist. Background and Current logic may quote the
    # ticket's own (product) ACs, so AC references are checked only from Rules onwards.
    for title, start, end in sections:
        name = canonical(title)
        for i in range(start, end - 1):
            text = lines[i]
            for m in refs(RULE_REF, text):
                bad = sorted(numbers(m.group(1)) - rule_nums)
                if bad and rule_nums:
                    add(i + 1, f"refers to rule {', '.join(map(str, bad))}, which does not exist")
            if name not in ("Background", "Current logic", None):
                for m in refs(AC_REF, text):
                    bad = sorted(numbers(m.group(1)) - ac_nums)
                    if bad and ac_nums:
                        add(i + 1, f"refers to AC{', AC'.join(map(str, bad))}, which does not exist "
                            "(write 'product AC<n>' or the P number if it means the ticket's own AC)")
            if name != "Open items":
                for m in refs(OPEN_REF, text):
                    bad = sorted(numbers(m.group(1)) - open_nums)
                    if bad:
                        add(i + 1, f"refers to open item {', '.join(map(str, bad))}, which does not exist")
                if re.search(r"(?i)not confirmed", text) and not re.search(r"(?i)open item", text):
                    add(i + 1, '"not confirmed" without a pointer to an open item')

    # Product requirements P1..Pn: each covered by an AC or an out-of-scope line.
    defined = {int(n) for n in re.findall(r"\bP(\d+)\b", body("Background"))}
    covered = set()
    for name in ("Acceptance Criteria", "Scope"):
        for m in re.finditer(r"\bPs?\s*(\d+(?:\s*[-–]\s*P?\d+)?(?:\s*(?:,|and)\s*P?\d+(?:\s*[-–]\s*P?\d+)?)*)", body(name)):
            covered |= numbers(m.group(1).replace("P", ""))
    for n in sorted(defined - covered):
        add(0, f"product requirement P{n} is not cited by any AC or Scope line")

    # No line numbers in the plan.
    if "Spec / Implementation Plan" in by_name:
        s, e = by_name["Spec / Implementation Plan"]
        for i in range(s, e - 1):
            if LINE_NUMBER.search(lines[i]):
                add(i + 1, "plan cites a source line number")

    # Evidence snippets (fenced blocks) in Current logic and Open items stay within three lines.
    for name in ("Current logic", "Open items"):
        if name not in by_name:
            continue
        s, e = by_name[name]
        fence = None
        for i in range(s, e - 1):
            if lines[i].strip().startswith("```"):
                if fence is None:
                    fence = i
                else:
                    if i - fence - 1 > 3:
                        add(fence + 1, f"code snippet of {i - fence - 1} lines in {name} (max 3)")
                    fence = None

    return sorted(set(problems))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("spec")
    parser.add_argument("--repo")
    args = parser.parse_args()
    problems = check(args.spec, args.repo)
    for line, msg in problems:
        print(f"{line}: {msg}" if line else msg)
    if not problems:
        print("OK")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
