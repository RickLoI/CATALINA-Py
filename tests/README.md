# Tests

Run: `python3 -I -m unittest discover -s tests -v` (seconds, standard library only).

The tests are differential: `tests/fixtures/*.expected` and the other fixtures were recorded by running the
**unmodified Java original** (CATALINA_Model V0.3) with small Java harnesses (not included in this repository), and the Python
output must be identical.

| File | What it checks |
|---|---|
| `test_formula.py` | 3,044 boolean/temporal expressions give the same result or failure as the Java evaluator |
| `test_protected.py` | the thread-safe lists behave like the Java ones |
| `test_long_memory.py` | state of the Long Memory after loading `case_study/Data` equals a dump taken from the Java |
| `test_phase3.py` | sorters, GLITTER plan library, signal broadcast, Global Workspace, XML maps, message flags, executive thread base class, a stress test |

The full-system traces of the case study (baseline, danger, low fuel) were compared with the Java by hand and are
not part of this suite because they run in real time (about 5 minutes).
