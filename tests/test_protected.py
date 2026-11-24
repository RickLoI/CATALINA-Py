"""Protected lists vs the observable behaviour of the Java classes (output recorded from the Java original)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from catalina.protected import AutoNamedProtectedList, ProtectedList  # noqa: E402


def j(value):
    """Format like Java's toString for lists/booleans/None."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(j(v) for v in value) + "]"
    return str(value)


class ProtectedListTest(unittest.TestCase):
    def test_matches_java(self):
        out = []
        lst = ProtectedList()
        lst.add("a"); lst.add("b"); lst.add("a"); lst.add(None)
        out.append("P1 " + j(lst.read()))
        arg = ["c", None, "a", "d"]
        lst.add_all(arg)
        out.append(f"P2 {j(lst.read())} arg={j(arg)}")
        out.append(f"P3 {j(lst.remove('b'))} {j(lst.remove('zzz'))} {j(lst.remove(None))} {j(lst.read())}")
        arg2 = ["a", None]
        out.append(f"P4 {j(lst.remove_all(arg2))} arg={j(arg2)} {j(lst.read())}")
        lst.set_list(["x", "y", "x"])
        out.append(f"P5 {j(lst.read())} get5={j(lst.get(5))} get1={j(lst.get(1))} size={lst.size()}")
        out.append(f"P6 {j(lst.remove_at(0))} {j(lst.remove_at(9))} {j(lst.read())}")
        snap = lst.read(); snap.append("mutated")
        out.append(f"P7 {j(lst.read())} {j(lst.is_empty())}")
        out.append(f"P8 {j(lst.remove_if(lambda s: s == 'y'))} {j(lst.remove_if(lambda s: s == 'q'))} "
                   f"{j(lst.read())} {j(lst.is_empty())}")
        lst.add("m"); lst.add("n")
        out.append(f"P9 {j(lst.read_and_clear())} {j(lst.read())}")

        auto = AutoNamedProtectedList()
        auto.add("a"); auto.add("a")
        out.append(f"A1 {j(auto.read())} inc={auto.get_inc_number()}")
        auto.add_all(["b", "b"])
        out.append(f"A2 {j(auto.read())} inc={auto.get_inc_number()}")
        auto.set_list(["c", "c"])
        out.append(f"A3 {j(auto.read())} inc={auto.get_inc_number()}")
        auto.add_all([]); auto.add_all(None)
        out.append(f"A4 {j(auto.read())} inc={auto.get_inc_number()}")

        expected = """P1 [a, b]
P2 [a, b, c, d] arg=[c, a, d]
P3 true false false [a, c, d]
P4 true arg=[a] [c, d]
P5 [x, y] get5=null get1=y size=2
P6 x null [y]
P7 [y] false
P8 true false [] true
P9 [m, n] []
A1 [a, a] inc=2
A2 [a, a, b, b] inc=4
A3 [c, c] inc=6
A4 [c, c] inc=6""".split("\n")
        self.assertEqual(out, expected)


if __name__ == "__main__":
    unittest.main()
