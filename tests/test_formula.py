"""Boolean evaluator against results produced by the original Java TBoolean_Expression_Evaluetor.

Fixtures: tests/fixtures/formula_cases.in and
formula_cases.expected (recorded from the Java original).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from catalina.formula import evaluate_expression  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _python_result(vars_text: str, expr: str) -> str:
    variables = {}
    for kv in vars_text.split(","):
        name, val = kv.split("=")
        variables[name] = val == "1"
    try:
        return "OK " + ("true" if evaluate_expression(expr, variables) else "false")
    except ValueError:
        return "EXC"


class FormulaDifferentialTest(unittest.TestCase):
    def test_matches_java(self):
        with open(os.path.join(FIX, "formula_cases.in")) as f:
            cases = [line.rstrip("\n").split("\t", 1) for line in f]
        with open(os.path.join(FIX, "formula_cases.expected")) as f:
            expected = [line.rstrip("\n") for line in f]
        self.assertEqual(len(cases), len(expected))
        mismatches = []
        for (vars_text, expr), want in zip(cases, expected):
            got = _python_result(vars_text, expr)
            if got != want:
                mismatches.append((vars_text, expr, want, got))
        self.assertEqual(mismatches[:10], [], f"{len(mismatches)} mismatches vs Java")


if __name__ == "__main__":
    unittest.main()
