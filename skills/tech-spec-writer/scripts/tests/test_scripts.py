"""Tests for the tech-spec-writer scripts. Run: python -I -m unittest discover -s <scripts>/tests"""
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
import check_spec  # noqa: E402

GOOD_SPEC = textwrap.dedent("""\
    # Technical Specification: PD-1 Example

    ## Background

    | Ref | Product text | AC |
    | --- | --- | --- |
    | P1 | Show the status | AC1 |
    | P2 | Email on failure | Out of scope |

    ## Rules

    1. Status is read from stored state.
    2. No MYOB call on page load.

    ## Current logic (verified in code, `main` @ `abc1234`, 2026-01-01)

    * `Foo.bar` reads the row.

    ## Scope

    **Out of scope:** the email (P2).

    ## Acceptance Criteria

    ### AC1: Status (rules 1, 2; P1)
    * Shows the status. Tests: JUnit 5 for `Foo`.

    ## Spec / Implementation Plan

    1. **Foo (AC1).** Change `Foo.bar`.

    ## Review Focus

    1. **Stale status.** Guarded by AC1 and rule 1.

    ## Open items

    1. **Which label?**
       - Found: `Foo.bar` returns a code.
       - Options: (a) one (b) two.
       - Recommended: (a), because it is simpler.
       - Waiting on: developer.
    """)


def run(*args, cwd=None):
    return subprocess.run([sys.executable, "-I", *args], capture_output=True, text=True, cwd=cwd)


class CheckSpecTest(unittest.TestCase):
    def check(self, text):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
            fh.write(text)
        try:
            return [msg for _, msg in check_spec.check(fh.name)]
        finally:
            os.unlink(fh.name)

    def test_good_spec_passes(self):
        self.assertEqual([], self.check(GOOD_SPEC))

    def test_section_order_and_decisions_section(self):
        text = GOOD_SPEC.replace("## Rules", "## Rules_tmp")
        text = text.replace("## Current logic", "## Rules").replace("## Rules_tmp", "## Current logic")
        text += "\n## Decisions\n\n| a | b |\n"
        problems = " ".join(self.check(text))
        self.assertIn("out of order", problems)
        self.assertIn('"Decisions" is not in the template', problems)

    def test_open_item_missing_parts(self):
        problems = self.check(GOOD_SPEC.replace("   - Waiting on: developer.\n", ""))
        self.assertIn("open item 1 lacks: Waiting on:", problems)

    def test_dangling_references(self):
        text = GOOD_SPEC.replace("Guarded by AC1 and rule 1.", "Guarded by AC4, rule 9 and open item 3.")
        problems = " ".join(self.check(text))
        self.assertIn("rule 9", problems)
        self.assertIn("AC4", problems)
        self.assertIn("open item 3", problems)

    def test_product_ac_reference_is_not_this_specs_ac(self):
        self.assertEqual([], self.check(GOOD_SPEC.replace("returns a code.", "returns a code (product AC9).")))

    def test_uncited_rule_and_uncovered_requirement(self):
        text = GOOD_SPEC.replace("2. No MYOB call", "2. No MYOB call\n3. Logged only").replace("the email (P2)", "the email")
        problems = " ".join(self.check(text))
        self.assertIn("rule 3 is not cited", problems)
        self.assertIn("P2 is not cited", problems)

    def test_not_confirmed_needs_open_item(self):
        self.assertIn('"not confirmed" without a pointer to an open item',
                      self.check(GOOD_SPEC.replace("reads the row.", "reads the row (not confirmed).")))
        self.assertEqual([], self.check(GOOD_SPEC.replace("reads the row.", "reads the row (not confirmed, open item 1).")))

    def test_line_numbers_and_long_snippets(self):
        text = GOOD_SPEC.replace("Change `Foo.bar`.", "Change Foo.java:42.")
        text = text.replace("* `Foo.bar` reads the row.", "* `Foo.bar` reads the row.\n```\na\nb\nc\nd\n```")
        problems = " ".join(self.check(text))
        self.assertIn("line number", problems)
        self.assertIn("snippet of 4 lines", problems)


class RepoTest(unittest.TestCase):
    """check_identifiers and search against a tiny git repository."""

    @classmethod
    def setUpClass(cls):
        cls.repo = tempfile.mkdtemp()
        files = {
            "src/Base.java": "public class Base { private String disabledOn; }",
            "src/Foo.java": "import java.time.Instant;\npublic class Foo extends Base {\n  void bar() {}\n  static final String MAX_RETRIES = \"x\";\n}",
            "src/Ems.js": "export const IntegrationTypes = { XERO: 1 };",
            "sql/seed.sql": "insert into app_config values ('my.config.key', '1');",
            "node_modules/lib/Foo.js": "bar bar bar",
            "app/orders.py": "class OrderService:\n    def refund(self):\n        pass\n",
        }
        for path, body in files.items():
            os.makedirs(os.path.join(cls.repo, os.path.dirname(path)), exist_ok=True)
            with open(os.path.join(cls.repo, path), "w", encoding="utf-8") as fh:
                fh.write(body)
        for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"]):
            subprocess.run(["git", "-C", cls.repo, *cmd], check=True)

    def identifiers(self, text):
        spec = os.path.join(self.repo, "..", "spec-%d.md" % id(text))
        with open(spec, "w", encoding="utf-8") as fh:
            fh.write(text)
        return run(os.path.join(SCRIPTS, "check_identifiers.py"), spec, "--repo", self.repo).stdout

    def test_existing_names_pass(self):
        out = self.identifiers("`Foo.bar()` `Foo.getDisabledOn()` `MAX_RETRIES` `my.config.key` "
                               "`src/Foo.java` `Instant` `IntegrationTypes.XERO` `RuntimeException` "
                               "`api/some/route` `a = b`")
        self.assertTrue(out.startswith("OK"), out)

    def test_non_java_declarations_pass(self):
        out = self.identifiers("`OrderService.refund()` `app/orders.py`")
        self.assertTrue(out.startswith("OK"), out)

    def test_missing_names_reported(self):
        out = self.identifiers("`Fooo` `Foo.baz` `NO_SUCH_CONST` `no.such.key` `src/Missing.java`")
        for name in ("Fooo", "Foo.baz", "NO_SUCH_CONST", "no.such.key", "src/Missing.java"):
            self.assertIn(f"`{name}`", out)

    def test_search_skips_node_modules_and_caps_output(self):
        out = run(os.path.join(SCRIPTS, "search.py"), "class", "--repo", self.repo, "--max", "1").stdout
        self.assertNotIn("node_modules", out)
        self.assertIn("not shown", out)


class TicketQuestionsTest(unittest.TestCase):
    def test_answer_in_who_answers_cell_is_flagged(self):
        out = run(os.path.join(SCRIPTS, "ticket_questions.py"), os.path.join(HERE, "fixtures", "ticket.md")).stdout
        q31 = out[out.index("Q31"):]
        self.assertIn("possible answer", q31.split("\n")[2])
        self.assertEqual(2, q31.count("marked open"))
        q12 = out[out.index("Q12"):out.index("Q31")]
        self.assertNotIn("possible answer", q12)
        self.assertIn("TO CONFIRM without a question id", out)


class ProductHashTest(unittest.TestCase):
    def test_whitespace_is_ignored_and_text_changes_are_not(self):
        import product_hash
        self.assertEqual(product_hash.fingerprint("AC1  Show\nbanner"), product_hash.fingerprint(" AC1 Show banner\n"))
        self.assertNotEqual(product_hash.fingerprint("AC1 Show banner"), product_hash.fingerprint("AC1 Hide banner"))
        self.assertRegex(product_hash.fingerprint("x"), r"^[0-9a-f]{8}$")


if __name__ == "__main__":
    unittest.main()
