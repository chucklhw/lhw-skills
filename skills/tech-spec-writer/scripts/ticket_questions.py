"""Index a ticket's own open questions: where each is marked open and where it may be answered.

Usage: python -I ticket_questions.py <ticket.md>

<ticket.md> is the ticket's description (and, optionally, its comments) saved as text. For every
question id such as Q31 the script lists each line that marks it open ([TO CONFIRM Q31]), its row
in an open-points table (question, and the "who answers" cell, where product owners often append
the answer), and every other line that mentions it. A row whose last
cell holds more than role names is flagged as a possible answer. Markers with no question id are
listed too. Reads only; changes nothing.
"""
import re
import sys

QID = re.compile(r"\bQ(\d+)\b")
# Words that only name who answers; anything beyond them in that cell may be the answer itself.
ROLES = re.compile(r"\b(?:po|product owner|product team|product|tech lead|security owner|developer|"
                   r"qa|ba|team|lead|owner|and|or)\b", re.I)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def short(text, limit=160):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit - 3] + "..."


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    raw = open(sys.argv[1], encoding="utf-8").read()
    # Jira markdown escapes brackets (\[TO CONFIRM Q31\]) and encodes line breaks inside cells.
    text = raw.replace("\\[", "[").replace("\\]", "]").replace("\\n", "\n")
    lines = text.split("\n")

    questions = {}
    unnumbered = []
    for no, line in enumerate(lines, 1):
        ids = QID.findall(line)
        is_row = line.lstrip().startswith("|") and line.count("|") >= 3
        row = cells(line) if is_row else []
        if is_row and row and QID.fullmatch(row[0]):
            q = questions.setdefault(int(row[0][1:]), {"marks": [], "row": None, "mentions": []})
            who = row[-1] if len(row) > 2 else ""
            residue = re.sub(r"[\W_]+", " ", ROLES.sub(" ", who)).strip()
            q["row"] = (no, short(row[1] if len(row) > 1 else ""), short(who, 300), bool(residue))
            continue
        marked = "TO CONFIRM" in line.upper()
        for qid in ids:
            q = questions.setdefault(int(qid), {"marks": [], "row": None, "mentions": []})
            (q["marks"] if marked else q["mentions"]).append((no, short(line)))
        if marked and not ids:
            unnumbered.append((no, short(line)))

    if not questions and not unnumbered:
        print("No question ids (Qn) or TO CONFIRM markers found.")
        return
    for qid in sorted(questions):
        q = questions[qid]
        print(f"Q{qid}")
        if q["row"]:
            no, question, who, answered = q["row"]
            print(f"  table row (line {no}): {question}")
            print(f"  who answers: {who}" + ("   <-- possible answer" if answered else ""))
        else:
            print("  no open-points table row")
        for no, line in q["marks"]:
            print(f"  marked open (line {no}): {line}")
        for no, line in q["mentions"]:
            print(f"  mentioned (line {no}): {line}")
    for no, line in unnumbered:
        print(f"TO CONFIRM without a question id (line {no}): {line}")


if __name__ == "__main__":
    main()
