"""Experiment harness: repeated scenario runs with optional variations, metrics and CSV output.

    from case_study.experiment import Variant, run_experiment
    rows = run_experiment(
        [Variant("baseline"),
         Variant("fast_loop", setup=lambda demo: None, loop_period_ms=25)],
        Scenario("danger", duration=60, tcs_answers=["0", "30"], stimuli=[...]),
        repetitions=3, speed=3.0, workers=3, csv_path="results.csv")

A ``Variant`` can change the code under test in two ways: ``setup(demo)`` is called after the demo
is built and before "Start AVA" (swap a function of ``demo.means_end_reasoner_function``, change a
threshold, remove an executive function ...), and ``loop_period_ms`` sets the 50 ms period of the
executive threads for that run. Each run happens in its own process (``workers`` in parallel), so
class-level changes never leak between runs. The simulated clock keeps the 50 ms : 1 s ratio at any
speed, but CPU work is not scaled: keep ``speed`` <= ~5 unless you are comparing relative effects.
"""
from __future__ import annotations

import csv
import multiprocessing as mp
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from catalina.agent_thread import AgentBaseThread
from catalina.clock import SimClock

from .demo import AutonomousVehicleDemo
from .scenario import Scenario, ScenarioRunner


@dataclass
class Variant:
    """One experimental condition: a name, an optional ``setup(demo)`` hook run before 'Start AVA' and an
    optional executive loop period.
    """
    name: str
    setup: Optional[Callable[[AutonomousVehicleDemo], None]] = None
    loop_period_ms: Optional[int] = None


def metrics(demo: AutonomousVehicleDemo) -> Dict[str, Any]:
    """Summary of a finished run (arrivals, city sequence, first/last arrival time, routes entered, 'no option'
    and 'route closed' counts, Global Workspace signals, events).
    """
    lines = demo.event_log.text_lines()
    arrivals = [m.group(1) for m in (re.search(r"I'm arrived in (\w+)", ln) for ln in lines) if m]
    arrival_events = [e for e in demo.event_log.of_kind("log") if "I'm arrived in" in e.data["text"]]
    return {
        "arrivals": len(arrivals),
        "cities": ">".join(arrivals),
        "first_arrival_sim_s": round(arrival_events[0].sim, 2) if arrival_events else None,
        "last_arrival_sim_s": round(arrival_events[-1].sim, 2) if arrival_events else None,
        "routes_entered": sum("I enter Route" in ln for ln in lines),
        "no_option": sum("I have no option" in ln for ln in lines),
        "route_closed": sum("I found the route closed" in ln for ln in lines),
        "gw_signals": len(demo.event_log.of_kind("gw_signal")),
        "events": len(demo.event_log.events),
    }


def _one_run(args) -> Dict[str, Any]:
    """Run one (variant, repetition) job and return its metrics row; executed in a separate process by
    ``run_experiment``.
    """
    variant, scenario, speed, rep, data_dir = args
    if variant.loop_period_ms is not None:
        AgentBaseThread.LOOP_PERIOD_MS = variant.loop_period_ms
    demo = AutonomousVehicleDemo(data_dir=data_dir, clock=SimClock(speed),
                                 scripted_answers=scenario.tcs_answers).start()
    if variant.setup is not None:
        variant.setup(demo)
    t0 = demo.clock.now()
    demo.start_av()
    ScenarioRunner(demo, scenario, t0).start()
    while demo.clock.now() - t0 < scenario.duration:
        demo.clock.sleep(0.1)
    demo.end_simulation()
    row = {"variant": variant.name, "scenario": scenario.name, "rep": rep, "speed": speed}
    row.update(metrics(demo))
    return row


def run_experiment(variants: List[Variant], scenario: Scenario, repetitions: int = 1, speed: float = 1.0,
                   workers: int = 1, csv_path: Optional[str] = None,
                   data_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Run every variant ``repetitions`` times on a scenario (in parallel with ``workers`` > 1), optionally
    writing the rows to a CSV file.
    """
    jobs = [(v, scenario, speed, r, data_dir) for v in variants for r in range(repetitions)]
    if workers > 1:
        with mp.get_context("fork").Pool(workers, maxtasksperchild=1) as pool:
            rows = pool.map(_one_run, jobs, chunksize=1)
    else:
        rows = [_one_run(j) if j[0].loop_period_ms is None else _fork_run(j) for j in jobs]
    if csv_path and rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return rows


def _fork_run(job) -> Dict[str, Any]:
    with mp.get_context("fork").Pool(1, maxtasksperchild=1) as pool:
        return pool.map(_one_run, [job])[0]
