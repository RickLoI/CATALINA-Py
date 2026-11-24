"""LongMemory loading + normalisation vs a dump produced by the original Java (TAgent construction).

tests/fixtures/long_memory_dump.expected was produced by a Java dump program on the
unmodified Java sources and the case study Data folder (462 lines).
"""
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from catalina.long_memory import LongMemory  # noqa: E402
from dump_state import dump  # noqa: E402


class LongMemoryTest(unittest.TestCase):
    def test_state_matches_java(self):
        lm = LongMemory()
        lm.initialize(os.path.join(ROOT, "case_study", "Data"))
        got = dump(lm)
        with open(os.path.join(ROOT, "tests", "fixtures", "long_memory_dump.expected")) as f:
            want = [line.rstrip("\n") for line in f]
        self.assertEqual(len(got), len(want))
        diffs = [(i, g[:200], w[:200]) for i, (g, w) in enumerate(zip(got, want)) if g != w]
        self.assertEqual(diffs[:5], [])

    def test_fixed_reasoner_beliefs_when_not_bug_compatible(self):
        lm = LongMemory(bug_compatible=False)
        lm.initialize(os.path.join(ROOT, "case_study", "Data"))
        epistemic = [d for d in lm.get_all_attentional_desires() if d.get_name() == "Inquiry_Estimated_Delay_prove"][0]
        names = epistemic.get_beliefs_name_for_reasoner()
        self.assertEqual(len(names), 22)
        self.assertIn("BL_Map", names)


if __name__ == "__main__":
    unittest.main()
