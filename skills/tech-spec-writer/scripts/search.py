"""Search the repository's tracked source without flooding the conversation.

Usage: python -I search.py <pattern> --repo <path> [--path <dir>] [--glob '*.java' ...]
                           [-i] [-w] [-F] [-l] [--max 60]

Runs `git grep` (tracked files only, so node_modules and build output are never searched) and
also skips bundled or generated files (vue-assets, minified JS, lock files). Prints at most --max
matching lines, each cut to 200 characters, then how many more there were. -l lists files only.
Pattern is an extended regular expression unless -F. Reads only; changes nothing.
"""
import argparse
import subprocess
import sys

EXCLUDES = [":(exclude,glob)**/node_modules/**", ":(exclude,glob)**/vue-assets/**",
            ":(exclude,glob)**/*.min.js", ":(exclude,glob)**/package-lock.json",
            ":(exclude,glob)**/build/**", ":(exclude,glob)**/dist/**"]
WIDTH = 200


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pattern")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--path", action="append", default=[], help="limit to this directory")
    parser.add_argument("--glob", action="append", default=[], help="limit to files like '*.java'")
    parser.add_argument("-i", action="store_true", help="ignore case")
    parser.add_argument("-w", action="store_true", help="whole words")
    parser.add_argument("-F", action="store_true", help="fixed string, not a regex")
    parser.add_argument("-l", action="store_true", help="list matching files only")
    parser.add_argument("--max", type=int, default=60)
    args = parser.parse_args()

    cmd = ["git", "-C", args.repo, "grep", "-I", "--no-color", "-l" if args.l else "-n"]
    cmd += [flag for flag, on in (("-i", args.i), ("-w", args.w)) if on]
    cmd += ["-F" if args.F else "-E", "-e", args.pattern, "--"]
    paths = [f"{p.rstrip('/')}/{g}" for p in args.path for g in args.glob] or args.path or args.glob
    cmd += [f":(glob)**/{p}" if p.startswith("*") else p for p in paths] + EXCLUDES

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode > 1:
        sys.exit(result.stderr.strip())
    out = result.stdout.splitlines()
    if not out:
        print("No matches.")
        return
    for line in out[:args.max]:
        if args.l:
            print(line)
            continue
        # Cut the matched text, not the path ("path:line:text").
        path, number, text = line.split(":", 2)
        text = text.strip()
        print(f"{path}:{number}: {text if len(text) <= WIDTH else text[:WIDTH - 3] + '...'}")
    files = len({l.split(":", 1)[0] for l in out})
    hidden = len(out) - args.max
    summary = f"{len(out)} {'files' if args.l else f'matching lines in {files} files'}"
    print(f"-- {summary}" + (f"; {hidden} not shown (narrow with --path/--glob or raise --max)" if hidden > 0 else ""))


if __name__ == "__main__":
    main()
