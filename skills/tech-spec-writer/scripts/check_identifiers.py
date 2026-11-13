"""Check that the code names a spec puts in backticks exist on the repository's current branch.

Usage: python -I check_identifiers.py <spec.md> --repo <path>

Checks file paths, classes (`Name`), members (`Name.member`, `Name.member()`, `Name#member`),
bare methods (`name()`), constants (`UPPER_CASE`) and config keys (`a.b.c`). Spans that are code
fragments, SQL, URLs, routes or placeholders are skipped. A class that is not declared in the
repository but is imported somewhere is treated as a library class and passes; so are members of
library classes.

Prints one line per name not found and exits 1, or prints "OK (<n> names checked)" and exits 0.
A name the spec introduces as new is expected to be reported. Reads only; changes nothing.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

IDENT = r"[A-Za-z_$][A-Za-z0-9_$]*"
NEW = " (fine only if the spec introduces it as new)"
# java.lang types are used without an import, so the import index cannot vouch for them.
JAVA_LANG = {"Object", "String", "Integer", "Long", "Short", "Byte", "Boolean", "Character", "Double",
             "Float", "Number", "Math", "System", "Thread", "Runnable", "Iterable", "Enum", "Record",
             "Exception", "RuntimeException", "Error", "Throwable", "IllegalArgumentException",
             "IllegalStateException", "UnsupportedOperationException", "NullPointerException",
             "Override", "Deprecated", "FunctionalInterface", "StringBuilder", "Void", "Class"}
EXTENSIONS = (".java", ".xml", ".sql", ".vue", ".js", ".ts", ".tsx", ".properties", ".yml",
              ".yaml", ".gradle", ".kts", ".md", ".py", ".vm", ".ftl", ".json", ".sh")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def classify(span):
    """Returns (kind, value) or None for spans that are not a single code name."""
    s = span.strip().rstrip(";")
    if (not s or " " in s or "<" in s or "*" in s or "..." in s or "://" in s
            or re.search(r"[=\"'{}\[\]]", s)):
        return None
    if "/" in s or s.endswith(EXTENSIONS):
        return ("path", s.rstrip("/"))
    m = re.fullmatch(rf"({IDENT})(?:\.|#)({IDENT})(?:\(\))?", s)
    if m and m.group(1)[0].isupper() and not m.group(1).isupper():
        return ("member", (m.group(1), m.group(2)))
    m = re.fullmatch(rf"({IDENT})\(\)", s)
    if m:
        return ("word", m.group(1))
    if re.fullmatch(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+", s):
        return ("word", s)
    if re.fullmatch(r"[A-Z][a-z0-9]+[A-Za-z0-9]*", s) and len(s) > 3:
        return ("class", s)
    if re.fullmatch(r"[a-z][a-z0-9_-]*(?:\.[a-z0-9_-]+){2,}", s):
        return ("word", s)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("spec")
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    repo = args.repo

    text = open(args.spec, encoding="utf-8").read()
    text = re.sub(r"```.*?```", "", text, flags=re.S)  # fenced blocks are snippets, not references
    names = {}
    for span in re.findall(r"`([^`\n]+)`", text):
        kind = classify(span)
        if kind:
            names.setdefault(kind, span)

    files = git(repo, "ls-files").splitlines()
    basenames = {}
    for f in files:
        basenames.setdefault(os.path.basename(f), []).append(f)
    components = {os.path.splitext(b)[0] for b in basenames}
    declared = set(re.findall(
        r"(?:class|interface|enum|record)\s+([A-Z]\w*)",
        git(repo, "grep", "-h", "-o", "-E", r"(class|interface|enum|record)\s+[A-Z][A-Za-z0-9_]*",
            "--", "*.java", "*.kt")))
    declared |= set(re.findall(
        r"(?:const|let|var|class|function)\s+([A-Z][\w$]*)",
        git(repo, "grep", "-h", "-o", "-E", r"(const|let|var|class|function)\s+[A-Z][A-Za-z0-9_$]*",
            "--", "*.js", "*.vue", "*.ts")))
    imported = set(re.findall(r"\.([A-Z]\w*);", git(
        repo, "grep", "-h", "-o", "-E", r"^import (static )?[A-Za-z0-9_.]+;", "--", "*.java")))

    def class_exists(name):
        return name in declared or name in components or name in imported or name in JAVA_LANG

    def class_files(name):
        return [os.path.join(repo, p) for ext in (".java", ".kt", ".vue", ".js", ".ts")
                for p in basenames.get(name + ext, [])]

    def has_member(name, member, depth=0):
        """True if the class or a superclass in this repository declares the member. A getter or
        setter also matches its field, because Lombok generates them from the field alone."""
        candidates = {member}
        m = re.fullmatch(r"(?:get|set|is)([A-Z]\w*)", member)
        if m:
            candidates.add(m.group(1)[0].lower() + m.group(1)[1:])
        for path in class_files(name):
            source = open(path, encoding="utf-8", errors="replace").read()
            if any(re.search(rf"\b{re.escape(c)}\b", source) for c in candidates):
                return True
            parent = re.search(rf"(?:class|interface)\s+{name}\b[^{{]*?\bextends\s+([A-Z]\w*)", source)
            if parent and depth < 4 and has_member(parent.group(1), member, depth + 1):
                return True
        return False

    # Bare words (methods, constants, config keys) are looked up in one git grep.
    # Class-like names not declared as classes may still be names in strings (a request or bean name).
    words = sorted({v for (k, v) in names if k == "word" or (k == "class" and not class_exists(v))})
    found_words = set()
    if words:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as fh:
            fh.write("\n".join(words))
        try:
            found_words = set(git(repo, "grep", "-h", "-o", "-F", "-f", fh.name).split("\n"))
        finally:
            os.unlink(fh.name)

    missing = []
    for (kind, value), span in sorted(names.items(), key=lambda x: x[1]):
        if kind == "path":
            exists = (os.path.exists(os.path.join(repo, value))
                      or any(f.endswith("/" + value) or ("/" + value + "/") in ("/" + f) for f in files))
            # Paths without an extension are often URLs, routes or branch names: report only files.
            if not exists and os.path.splitext(value)[1]:
                missing.append(f"`{span}`: no such file")
        elif kind == "class":
            if not class_exists(value) and value not in found_words:
                missing.append(f"`{span}`: no class, interface, enum or component of that name{NEW}")
        elif kind == "member":
            cls, member = value
            if not class_exists(cls):
                missing.append(f"`{span}`: no class {cls}{NEW}")
            elif class_files(cls) and not has_member(cls, member):
                missing.append(f"`{span}`: {cls} has no member {member}{NEW}")
        elif value not in found_words:
            missing.append(f"`{span}`: not found anywhere in the repository{NEW}")

    for line in missing:
        print(line)
    if not missing:
        print(f"OK ({len(names)} names checked)")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
