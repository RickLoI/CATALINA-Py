# catalina_py

To install and run: see `INSTALL.md` (Italian: `INSTALL.it.md`). To work on the code: `docs/DEVELOPER_GUIDE.md` (Italian: `docs/GUIDA_SVILUPPATORE.md`).

Python port of the CATALINA agent (Java V0.3, "Case Study Journal 001"), for variations and experiments.
Design decisions agreed: executive functions run as real threads (Buehler's parallel executive system),
headless core + GUI that only reads the event log, Java-compatible behaviour first and fixes later.

## Layout
- `catalina/` the engine. Names follow the Java ones in snake_case (`TBelief.Get_Name()` -> `Belief.get_name()`).
- `case_study/` the autonomous-vehicle case study (domain, map, functions, scenarios, experiments, GUI).
- `case_study/Data/` the case study XML files (from the Java repository; `Beliefs.xml` is the updated version supplied by the Java author and `Critical_Beliefs.xml` is intentionally empty).
- `tools/run_scenario.py` headless scenario runner (prints the agent log); the other files in `tools/` are test helpers.
- `docs/` developer guide.
- `tests/` differential tests against output recorded from the Java original (see `tests/README.md`); run with `python3 -I -m unittest discover -s tests -v`.

## Run it
- Headless, 60 simulated seconds, speed 1: `python3 tools/run_scenario.py 60 "never" 0` (prints the agent log).
- GUI (browser, stdlib only): `python3 -m case_study.gui` then "Start AVA". Speed slider 0.1x-100x, clock pause,
  buttons for danger / low fuel, text field for the answers of the traffic control service (danger type 0-2, then 1-100).
- Experiments: `case_study/experiment.py` (`Variant`, `run_experiment`, CSV out); scenarios: `case_study/scenario.py`
  (`Stimulus(kind, at, when, delay)`, scripted TCS answers).

## Simulated clock (`catalina/clock.py`)
Every wait of the agent (50 ms loops) and of the car (1 s per step) goes through `demo.clock`. `SimClock(speed)` scales
them together, so their ratio is the Java one at any speed; speed can be changed and the clock paused while running.
**CPU time is not scaled**: generating the options for thousands of paths takes ~2 s of real time (Java: much less),
so above ~5x the agent reasons slower *in simulated time* than at 1x. Use high speeds to compare relative effects of
variations, 1x-3x when you need Java-like timing. Java's own timings are not reproducible either (thread races: one
Java run died at start with a NullPointerException in `Execute_Movement_Go_TO_Route`).

## Credits and license
This is a Python port of the CATALINA reference implementation (Java, branch V0.3,
[CATALINA_Model](https://github.com/CATALINA-Architecture/catalina_model)). The architecture is described in:

- Cossentino, M., Averna, G., Pilato, G., Mylopoulos, M., & Mylopoulos, J. (2025). The agent working cycle in CATALINA.
  In G. Ciatto, E. Blanzieri, & V. Mascardi (Eds.), *Proceedings of WOA 2025, the 26th Workshop "From Objects to Agents"*
  (Vol. 4028, pp. 2-18). Trento, Italy: CEUR-WS.org. <https://ceur-ws.org/Vol-4028/paper11.pdf>
- Cossentino, M., Pilato, G., Averna, G., Mylopoulos, M., & Mylopoulos, J. (2025). The agent metamodel in CATALINA
  (Cognitive Agent prActical reasoning archItecture). In *Multi-Agent Systems: 22nd European Conference, EUMAS 2025,
  Bucharest, Romania, September 3-5, 2025, Proceedings, Part I* (pp. 163-178). Springer.
- Cossentino, M., Pilato, G., Averna, G., Mylopoulos, M., & Mylopoulos, J. (2025). Practical reasoning with attention
  mechanisms. In *2025 International Conference on Simulation, Modeling, and Programming for Autonomous Robots (SIMPAR)*
  (pp. 1-6). IEEE. doi: 10.1109/SIMPAR62925.2025.10979194

Licensed under the Apache License 2.0 (see `LICENSE` and `NOTICE`), the same license as the Java original. See also `CITATION.cff`.

## Fidelity to the Java
The port was verified against the real Java (differential runs of the whole case study: baseline, danger, low fuel and
several TCS answers give the same agent log up to the end of the shorter run). Not verified against Java: long runs
(> 110 s), combinations of several dangers, a fuel stimulus during a danger. The Java quirks listed below are kept on
purpose and are also documented in the module docstrings.

## Known Java quirks (kept for now, each one checked in the Java source)
1. Epistemic loader reads the tag `Beliefs_for_Reasoner` (container) instead of `Belief_for_Reasoner`:
   each epistemic desire gets ONE string with all belief names. Confirmed identical in the Java dump.
   `LongMemory(bug_compatible=False)` reads the items instead.
2. `Map_Green_Desires` / `Map_Quality_Desires` are never filled: `get_*_desires_by_names` returns [].
3. The boolean evaluator keeps its variables in a static map and substitutes names with `replaceAll`
   (names contained in other names can corrupt a formula). The port uses per-instance variables and whole
   identifiers; same results in the case study (single-belief formulas, variables reset before each use).
4. `TBelief.Clone()` returns a plain belief (a cloned `TStimulus` loses its saliency and class).
5. `TPractical_Desire` sets `Until_Start = global_End` (typo, never read).
6. The Java loaders of the epistemic desires accumulate lists across desires (declared outside the loop);
   irrelevant here (one epistemic desire in the data), so the port builds them per desire.
7. `Critical_Beliefs.xml` is intentionally empty (confirmed by the Java author; older Data folders lacked it and the
   loader just printed an error). The updated `Beliefs.xml` adds `Confidence` and `Is_Stimulus` per belief: the
   port ignores them (no logic uses them), as the V0.3 Java does.
8. `TMap_Belief_To_Salience_Stimuli` builds its path with a Windows `\\` separator, so the original does not
   find `Map_Belief_To_Salience_Stimuli.xml` on Linux/macOS.
9. `broadcast_signal(Updated_Satisfied_Desires)` raises the Perceptions flag (copy/paste): subscribers of
   `Updated_Satisfied_Desires` are never notified that way. `broadcast_signal` has no case at all for
   `Updated_Preconditions` and the `Internal_Signals_*` contracts.
10. In `broadcast()`, delete/satisfied-intention messages are forwarded with `Read_Sender()` then
    `Read_Data_and_Clean()`: the FIRST subscriber receives sender and data, the others an empty message.
    Internal-signal messages also carry the sender name as their type.
11. Subscribers are a Java `HashSet` (identity-hash order); the port keeps insertion order. So "first
    subscriber" in quirk 10 is arbitrary in Java and the registration order here. The comparison treated those
    queues as a multiset over the subscribers.
12. `TGLITTER_Trie.Create_Plan` always returns false; `Get_Plans` throws a NullPointerException when the path
    exists but ends on a node without tasks (`JavaNullPointerError` in the port); adding a pre-condition node
    REPLACES the value map stored under that name; the quality layer ignores the value.
13. `TAction.Copy_Action` never copies `Formula_Pre_Conditions` (it copies `Formula_Invariants` twice), so
    `Clone()` loses it.
14. `Add_Uninhibited_Conscious_Data` / `Remove_...` rebuild the name->belief and name->region maps from their
    arguments only, not from the whole lists.
