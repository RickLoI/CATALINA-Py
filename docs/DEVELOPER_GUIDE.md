# CATALINA (Python): developer guide

(Italian version: [GUIDA_SVILUPPATORE.md](GUIDA_SVILUPPATORE.md))

This guide explains how the code is organised, how data flows between components, and where to intervene to build
variations and experiments. The details of every class and function are in the code docstrings (each module starts with a
docstring describing its role and the Java behaviours deliberately kept).
Installation and usage commands: `INSTALL.md`. How fidelity to the Java was verified: `README.md`.

## 1. What it is

A Python port of the CATALINA agent (Java V0.3, "Case Study Journal 001"): a BDI agent with a Global Workspace
(Baars) and executive functions (Buehler). The case study is an autonomous vehicle that visits cities on a map
of 47 cities and 132 routes (66 bidirectional edges), with dangers on routes and low fuel.

Agreed design choices:
- executive functions are real threads running in parallel (as in Buehler's executive system);
- the core runs without a GUI; the GUI only reads the event log;
- Java-compatible behaviour first (even where the Java has defects), fixes later;
- differential verification against the original Java.

## 2. Folder structure

| Folder | Content |
|---|---|
| `catalina/` | the architecture engine (independent of the case study) |
| `case_study/` | the case study: domain, map, functions, wiring, scenarios, experiments, GUI |
| `case_study/Data/` | the case-study XML files (desires, beliefs, sensors, actions...), from the Java repository, with the updated `Beliefs.xml` and the empty `Critical_Beliefs.xml` |
| `tests/` | differential tests against output recorded from the Java (see `tests/README.md`) |
| `tools/` | `run_scenario.py` (headless scenario runner) and helpers used by the tests |
| `docs/` | this guide |

### 2.1 `catalina/` (engine)

| Module | Role |
|---|---|
| `agent.py` | `Agent`: creates the Long Memory, the Global Workspace and the executive functions; getters and registration API |
| `agent_thread.py` | `AgentBaseThread`: base of the executive threads (loop, pause, stop) |
| `clock.py` | `RealClock` and `SimClock` (simulated clock with speed and pause) |
| `global_workspace.py` | `GlobalWorkspace`: shared blackboard and hub of the update signals |
| `messages.py` | the "mailbox" of flags and message queues of each component |
| `long_memory.py` | `LongMemory`: beliefs, predicates, desires, regions; XML loading and normalisation |
| `memory_maintenance.py` | filtered stimuli -> beliefs step (Working Memory Maintenance) |
| `model.py`, `desires.py`, `plan.py` | data model: predicates, beliefs, stimuli, regions; desires; actions, options, intentions |
| `formula.py` | boolean and temporal formulas |
| `plan_library.py`, `sorters.py` | GLITTER plan library (trie) and canonical sorting of expressions |
| `handlers.py` | the "name -> function" registries used by the executive functions |
| `executive_*.py` | the executive functions (see 3.2) |
| `action_control.py` | action execution through functions registered by name |
| `protected.py`, `conscious_data.py`, `desire_data.py`, `maps.py`, `xmlio.py`, `enums.py` | thread-safe containers, conscious data, desire bundles, XML-based maps, XML helpers, enumerations |

### 2.2 `case_study/`

| Module | Role |
|---|---|
| `demo.py` | `AutonomousVehicleDemo`: wires everything together (equivalent of the Java `Start()`) |
| `environment.py`, `map_data.py`, `domain.py` | map, routes, paths (DFS) and simulations; coordinates generated from the Java; enums (`TCity`, ...) |
| `functions_perception.py` | sensors, stimulus extraction, saliency filters, belief updates |
| `functions_desires.py` | promotion of exogenous desires (danger, low fuel) |
| `functions_inhibition.py` | which beliefs and regions stay "conscious" for each desire; GW callbacks |
| `functions_reasoner.py` | option generation (means-end), green/quality filters, deliberation |
| `functions_execution.py` | the 10 executable actions (movement, waiting, refuelling...) |
| `traffic_control.py`, `map_panel.py`, `common.py` | simulated traffic-control service, map/car panel model, utilities |
| `events.py` | event log (replaces the Java `Log_Memo` and the GW window) |
| `scenario.py`, `experiment.py` | scripted stimuli and run loop; repeated experiments with variants and CSV |
| `gui.py`, `gui_page.html` | browser GUI (standard-library HTTP server) |
| `javacompat.py` | Java collection behaviours the case study depends on (`HashMap` ordering, `ConcurrentModificationException`) |

Names follow the Java ones in snake_case (`TBelief.Get_Name()` becomes `Belief.get_name()`), so the code can be
compared with the original line by line. Each module cites the corresponding Java classes in its docstring.

## 3. How it works

### 3.1 Overview

```
  sensors ──> [Perception] ──stimuli──> [Memory Maintenance] ──beliefs──┐
                                                                          v
  [Desire Handler] <── signals ── GLOBAL WORKSPACE (blackboard + broadcast) ──> [Inhibition]
        |  active desires                     ^   |                           (what is conscious)
        v                                     |   v
   [Reasoner]: options -> filters -> deliberation ──intentions──> [Attention] (thresholds)
                                                |
                                         [Switching] ──action──> Action Control ──> registered function
```

All components read and write data in the Global Workspace and wake each other up with update signals
(`broadcast_signal`). None calls another directly.

### 3.2 The executive functions

| Executive (file) | When it acts | What it does |
|---|---|---|
| Perception (`executive_perception.py`) | every cycle | queries the sensors, extracts stimuli, assigns saliency, filters with the thresholds, publishes the filtered stimuli |
| Memory Maintenance (`executive_memory.py`) | filtered stimuli arrive | updates beliefs with the function registered for the stimulus type and publishes the stimuli |
| Desire Handler (`executive_desires.py`) | data/threshold/stimulus signals | cancels failed or satisfied intentions, demotes low-saliency desires, promotes exogenous (from stimuli) and endogenous desires (activation condition true and sufficient saliency) |
| Inhibition (`executive_inhibition.py`) | thresholds change | decides which beliefs, desires and regions stay "conscious" according to the selected intentions |
| Reasoner (`executive_reasoner.py`) | active desires change | means-end (options), Finally operator, green and quality filters, deliberation, selected intentions |
| Attention (`executive_attention.py`) | selected intentions change | focuses (high thresholds) if the first intention has options, otherwise defocuses (0.3/0.3) |
| Switching (`executive_switching.py`) | only while the agent is focused | executes the plan of the first intention one action at a time, checking pre/post-conditions |
| Resource Allocation (`executive_resources.py`) | not started by the case study | management of critical beliefs |

Every executive extends `AgentBaseThread` (`agent_thread.py`). The loop is the Java one:

```
wait if paused -> wait 50 ms (on the agent clock) -> execute()
```

`execute()` usually checks the flags of its own mailbox (`self.message_handler`) and does nothing if none of the
signals it subscribes to has arrived. Subscriptions are declared in `insert_in_list_update_contract()`
(signal types are in `enums.TypeUpdateContract`).

### 3.3 The Global Workspace and the signals

`global_workspace.py` does two things:
1. it holds, under locks, the shared lists: thresholds, stimuli, non-inhibited beliefs/desires/regions, preconditions, intentions,
   plan library;
2. it propagates signals: `broadcast_signal(contract)` raises the corresponding flag in its own mailbox and `broadcast()` copies it
   into the mailbox of every executive subscribed to that contract.

Flags and message queues are in `messages.py`. Signals carrying data (cancel option, cancel intention, satisfied
intention) travel in message queues with sender and data.

The Java locks (four `ReentrantReadWriteLock`) are re-entrant mutexes; the acquisition order is the Java one.
The GW callbacks (`global_workspace_call_back`, `general_call_back`, in `case_study/functions_inhibition.py`)
run inside the GW, under its locks: keep them short.

### 3.4 Life cycle of a desire (full flow)

1. **Loading.** `LongMemory.load_data` reads the XML files in `Data/` (predicates, beliefs, green/quality/epistemic/practical desires)
   and normalises them (resolves names into objects).
2. **Promotion.** The Desire Handler looks for *standing* practical desires whose `Trigger_Condition_Formula` is true and whose saliency
   exceeds the threshold; once promoted they become *Active* (`GlobalWorkspace.mark_as_active_desires`). In `Practical_Desires.xml`:
   `Visit_Frankfurt` (saliency 0.4), `Visit_Paris` (0.5), `Visit_Rome` (0.8, activates after `BL_City_Visited_Paris`).
   Stimuli (danger, low fuel) instead generate exogenous desires through `case_study/functions_desires.py`.
3. **Reasoning.** The Reasoner calls the means-end function registered by desire name (practical) or by belief type
   (epistemic): it produces the *options* (for `Visit_<city>`: one option for each simple path found by the DFS, with its
   actions `Initialize_Way`, `GO_TO_Route`, `GO_TO_Step`). Then: Finally operator (discards options outside the interval),
   green/quality filters (pollution, scenery, speed), deliberation (chooses the intention).
4. **Attention and inhibition.** Attention updates the thresholds; Inhibition decides which beliefs/regions stay conscious for
   the chosen intention (the functions of `functions_inhibition.py`).
5. **Execution.** Switching executes one action at a time: it checks the preconditions, calls the function registered in Action
   Control for that action name (`functions_execution.py`), checks the postconditions, and when the option is complete
   it signals the Desire Handler (intention satisfied, the plan goes into the library) or cancels it.

### 3.5 The case study, step by step

`AutonomousVehicleDemo.start()` (`case_study/demo.py`) follows the Java `Start()`:
1. builds `MapPanelModel` and the `Agent` (which loads the XML data);
2. `initialize_data_simulation`: creates the map (`create_map`), adds a `RegionSimulation` for each route to the Long Memory and
   puts the map in the predicate of `BL_Map`;
3. registers the function groups in the Java order: perception (sensors, extraction, filters), memory maintenance,
   belief and region inhibition, exogenous promotion, reasoner (means-end, filters, deliberation), action execution;
4. suspends the seven executives.

`start_av()` ("Start AVA") starts and resumes the seven executives, sends a broadcast and sets the thresholds to 0.3/0.3.

Where things are registered (useful when adding elements):

| Element | Where it is registered | Registration key |
|---|---|---|
| sensor | `FunctionsForPerceptionProcessing` (`functions_perception.py`) | sensor name (`Front_Virtual_Camera`, `Traffic_Control_Service`, `Fuel_Sensor`) |
| stimulus extraction | `FunctionsForInformationExtraction` | sensor name |
| stimulus saliency/filter | `FunctionsForStimulusFiltering` | stimulus type (`BLTS_Stimulus_...`); base saliencies are in `Map_Belief_To_Salience_Stimuli.xml` |
| belief update | `FunctionsForGWMemoryMaintenanceUpdateBeliefFunction` | stimulus type |
| exogenous desire | `FunctionsForExogenousDesirePromotion` | stimulus type |
| means-end | `FunctionsForMeansEndReasoner` | practical desire name / belief type of the epistemic desire |
| belief and region inhibition | `FunctionsForInhibitionFunction` | desire name / belief type |
| green / quality filters | `FunctionsForFilteringDesiresFunction` | green desire type; a single quality filter |
| deliberation | `FunctionsForDeliberationProcess` | one function |
| action | `FunctionsForOptionExecution` | action name (the ten actions are listed in `add_function_to_switching_function`) |

For the danger stimulus: the camera sees it (`see_road_in_front`, **only once per run**, as in the Java), Memory
Maintenance marks the route `Under_maintenance`, the epistemic desire `Inquiry_Estimated_Delay` is born, and its option has two actions:
`Ask Danger Type on the road` (questions to the traffic-control service: danger type and duration) and
`Decide_To_Continue_or_Not`; the service data come back as a stimulus and the practical desire is replanned from the damaged route.

### 3.6 Simulated clock

All the agent's waits (the 50 ms loop, the 1 s car step) go through `agent.clock`. `SimClock(speed)` scales them
together, so the 50 ms : 1 s ratio stays the Java one at any speed; speed and pause can be changed while the
agent is running. Computation time is **not** scaled: generating the options for thousands of paths takes about 2 real seconds,
so above ~5x the agent "reasons" more slowly in simulated time. For comparisons with the Java stay at 1x-3x; to compare
relative effects of variations you can go higher.

### 3.7 Event log and GUI

`case_study/events.py`: everything observable is an `Event(seq, sim, wall, thread, kind, data)`. Kinds:

| kind | content |
|---|---|
| `log` | text that the Java wrote in the `Log_Memo` |
| `car_move` | `frm`, `to`, `duration` (simulated seconds), `route`, `step` |
| `gw_update`, `gw_signal` | summaries of the Global Workspace callbacks |
| `stimulus` | scripted stimulus (button) |
| `scenario` | start/end of run |

`event_log.text_lines()` returns the Java log lines; `dump_jsonl(path)` saves everything. The GUI (`gui.py` + `gui_page.html`) is a
small HTTP server: the page polls `/api/state?since=N`, animates the car by linear interpolation over the `car_move` events with respect to
simulated time, and sends commands to `/api/cmd/<name>` (start, suspend, resume, danger, low_fuel, tcs, speed, pause, unpause, reset,
save_log). For a different GUI (Tk, Qt...) just subscribe to `EventLog.subscribe` and call the methods of `AutonomousVehicleDemo`
(`start_av`, `send_a_danger`, `send_low_fuel_signal`, `submit_tcs_response`, `end_simulation`).

## 4. Variations and experiments

### 4.1 Scenarios (`case_study/scenario.py`)

```python
from case_study.scenario import Scenario, Stimulus, log_contains, run_scenario

sc = Scenario("danger_on_115", duration=80, tcs_answers=["0", "30"],      # danger type 0, duration 30 slots
              stimuli=[Stimulus("danger", when=log_contains("I enter Route: [115]"), delay=1.5)])
demo = run_scenario(sc, speed=1.0)
print(demo.event_log.as_text())
```

`Stimulus(kind, at, when, delay)`: `kind` is `"danger"` or `"low_fuel"`; it fires when `at` simulated seconds have passed and `when(demo)` is true
(plus `delay` seconds). `tcs_answers` are the answers to the traffic-control service questions, in order.

### 4.2 Experiments (`case_study/experiment.py`)

`Variant(name, setup=None, loop_period_ms=None)`: `setup(demo)` is called after construction and before "Start AVA", and can change
anything (registered functions, thresholds, parameters). Each run executes in a separate process (`workers` in parallel), so
changes do not propagate between runs.

Examples tried (45 simulated seconds, speed 2x, one run per variant):

```python
from case_study.experiment import Variant, run_experiment
from case_study.scenario import Scenario

def faster_car(demo):
    demo.functions_for_plan_execution.global_time_to_move = 0.5      # simulated seconds per step (default 1.0)

def no_quality_filter(demo):
    reasoner = demo.agent.get_executive_reasoner_function()
    reasoner.set_quality_desire_filtering_process(lambda d, b, r, i: None)   # None = options unchanged

rows = run_experiment([Variant("default"), Variant("faster_car", setup=faster_car),
                       Variant("loop_25ms", loop_period_ms=25), Variant("no_quality", setup=no_quality_filter)],
                      Scenario("baseline", duration=45), repetitions=1, speed=2.0, workers=4, csv_path="results.csv")
```

Observed results: `default` and `loop_25ms` reach 5 cities in 45 s; `faster_car` reaches 8 (Pamplona, Barcelona, Marseille,
Paris, Marseille, Rome, Marseille, ...); without the quality filter the car chooses other paths (Barcelona, Marseille, Zurich, Venice, Munchen...).
Per-run metrics (`metrics()`): arrivals, city sequence, times of first and last arrival, routes travelled, "no option",
"route closed", GW signals, events.

Other useful points of intervention:
- `global_workspace.set_default_saliency_thresholds` / `set_default_attention_thresholds`: default thresholds;
- `AgentBaseThread.LOOP_PERIOD_MS` (or `Variant(loop_period_ms=...)`): loop period;
- `FunctionsForDeliberationProcess.deliberation_process_function` (`functions_reasoner.py`): how many intentions are pursued and in which order;
- saliencies and rewards in `Data/*.xml` (the XML files use the decimal comma);
- `Environment`/`create_map`: map, route colours (`MyCollections` in `domain.py`), weights.

## 5. How to extend

**New practical desire (e.g. another city).** Add the desire to `Data/Practical_Desires.xml` and the `BL_Destination_<City>` beliefs to
`Data/Beliefs.xml` (with their predicates if needed), then register the means-end function under its name
(`reasoner_register_practical_function`, see `add_functions_to_means_end_reasoner`: today the names are listed in the code) and the inhibition functions
(`add_lists_for_practical_desires` in `functions_inhibition.py`). Note: the code also registers `Visit_Cadiz`, which is not in the XML files.

**New sensor and stimulus.** Add the sensor to `Sensors.xml`; in `functions_perception.py`: the name in `self.sensors`/`sensors_avaible`, a function that
produces a `Perception`, a stimulus extraction function, a saliency filter and a belief update (all registered by stimulus type);
if it must generate a desire, add the function in `functions_desires.py`.

**New action.** Write the function `(global_workspace, action, map_beliefs) -> ActionExecutionResult` in `functions_execution.py` and register it in
`add_function_to_switching_function` with the same name used in the actions created by the means-end. The result carries `beliefs_to_change`
(a dictionary `belief name -> [field, value, ...]`) that the framework applies to the beliefs.

**New executive function.** Subclass `AgentBaseThread` with `insert_in_list_update_contract()` (which signals it answers) and `execute()`
(one iteration); create it in `Agent.__init__`, add it to `Agent.executives()` and start/resume it in `MapPanelModel.start_av`.
If a new signal type is needed: an entry in `TypeUpdateContract` and in `_SIGNAL_FLAG` / `_BROADCAST_FLAGS_*` of `global_workspace.py`, a flag in `messages.py`.

**New green/quality filter.** `register_green_filtering_function(type, function)`; the quality filter is unique (`set_quality_desire_filtering_process`).

## 6. Fidelity to the Java

- The port was compared with the real Java on the log (`event_log.text_lines()`): the sequences of `I enter Route ...`, `I'm arrived in ...` lines,
  the questions/answers of the traffic service and the decision messages, on the common prefix of the two traces. The Java is not deterministic in timing (races between threads).
- Java behaviours deliberately kept (defects included) are listed in `README.md` ("Known Java quirks") and in the docstrings of the
  `functions_*.py` modules. To fix one, do it in a single place and compare the agent log before and after.

## 7. Known limits

- Performance: option generation is the bottleneck (thousands of paths per desire, ~2 real seconds).
- Not compared with the Java: simulations longer than about 110 seconds, combinations of several dangers, a fuel stimulus during a danger.
- The camera works only once per run and the GPS sensor is ignored (as in the Java).
- The Java can fail at start-up non-deterministically (an exception in `Execute_Movement_Go_TO_Route` was observed once): it is a race in the
  original code, not in the port.
- No automated GUI test; it was tried by hand with an automated browser (start, danger, TCS answers, low fuel, suspend/resume, pause,
  reset, slider).
