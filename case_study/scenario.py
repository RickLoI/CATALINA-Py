"""Scripted stimuli (replace the two GUI buttons) and the run loop of an experiment.

A ``Scenario`` lists stimuli, each fired when the simulated time since the start of the run reaches
``at`` and (optionally) ``when(demo)`` is true, plus the answers given to the traffic-control
questions. ``run_scenario`` starts the agent, plays the scenario on the demo clock, waits for the
duration and stops everything; the result is the event log.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from catalina.clock import SimClock

from .demo import AutonomousVehicleDemo


@dataclass
class Stimulus:
    """A scripted press of the 'danger' or 'low_fuel' button: fired once the run time reaches ``at`` and
    ``when(demo)`` holds, after ``delay`` more simulated seconds.
    """
    kind: str                                   # "danger" | "low_fuel"
    at: float = 0.0                             # simulated seconds since the start of the run
    when: Optional[Callable[[AutonomousVehicleDemo], bool]] = None   # extra condition, polled
    delay: float = 0.0                          # simulated seconds to wait after ``when`` first holds


@dataclass
class Scenario:
    """A run description: name, duration (simulated seconds), stimuli and the scripted answers to the traffic-
    control questions (danger type index, then duration 1-100).
    """
    name: str = "baseline"
    duration: float = 45.0                      # simulated seconds
    stimuli: List[Stimulus] = field(default_factory=list)
    tcs_answers: List[str] = field(default_factory=list)   # danger type index, then duration (1-100), ...


def on_route(demo: AutonomousVehicleDemo) -> bool:
    """True while the car is on a route (``BL_Position_Route`` >= 0)."""
    route = demo.belief_value("BL_Position_Route")
    return route is not None and route >= 0


def log_contains(text: str) -> Callable[[AutonomousVehicleDemo], bool]:
    return lambda demo: any(text in line for line in demo.event_log.text_lines())


class ScenarioRunner(threading.Thread):
    """Thread that fires the stimuli of a scenario on the demo clock."""
    def __init__(self, demo: AutonomousVehicleDemo, scenario: Scenario, t0: float):
        super().__init__(name="Scenario", daemon=True)
        self.demo, self.scenario, self.t0 = demo, scenario, t0

    def run(self) -> None:
        """Wait, in time order, for each stimulus' time and condition, then send the danger / low-fuel signal.
        """
        demo = self.demo
        pending = sorted(self.scenario.stimuli, key=lambda s: s.at)
        while pending and not demo.stopping.is_set():
            stimulus = pending[0]
            if demo.clock.now() - self.t0 >= stimulus.at and (stimulus.when is None or stimulus.when(demo)):
                if stimulus.delay > 0:
                    demo.clock.sleep(stimulus.delay)
                pending.pop(0)
                if stimulus.kind == "danger":
                    demo.send_a_danger()
                elif stimulus.kind == "low_fuel":
                    demo.send_low_fuel_signal()
                else:
                    raise ValueError("unknown stimulus kind: " + stimulus.kind)
            else:
                demo.clock.sleep(0.05)


def run_scenario(scenario: Scenario, speed: float = 1.0, data_dir: Optional[str] = None,
                 echo: bool = False) -> AutonomousVehicleDemo:
    """Build and start a demo, play the scenario for ``scenario.duration`` simulated seconds at ``speed``, stop
    everything and return the demo (read ``demo.event_log``).
    """
    demo = AutonomousVehicleDemo(data_dir=data_dir, clock=SimClock(speed),
                                 scripted_answers=scenario.tcs_answers, echo=echo)
    demo.start()
    demo.event_log.emit("scenario", phase="start", name=scenario.name, speed=speed)
    t0 = demo.clock.now()
    demo.start_av()
    runner = ScenarioRunner(demo, scenario, t0)
    runner.start()
    while demo.clock.now() - t0 < scenario.duration:
        demo.clock.sleep(0.1)
    demo.event_log.emit("scenario", phase="end", name=scenario.name)
    demo.end_simulation()
    return demo
