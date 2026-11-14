"""Print a short fingerprint of a ticket's product text, to detect that it changed since a spec was written.

Usage: python -I product_hash.py <product-text.md>

<product-text.md> holds the ticket description followed by its comments, as plain text, leaving out
the spec's own comment. Whitespace is collapsed first, so reformatting does not change the result.
Prints 8 hex characters. Reads only; changes nothing.
"""
import hashlib
import re
import sys


def fingerprint(text):
    """Return 8 hex characters identifying `text` with all runs of whitespace collapsed."""
    normal = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(normal.encode("utf-8")).hexdigest()[:8]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as handle:
        print(fingerprint(handle.read()))


if __name__ == "__main__":
    main()
