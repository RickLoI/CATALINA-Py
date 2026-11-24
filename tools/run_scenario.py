"""Run a danger scenario like the Java Danger_Driver and print the log.

usage: run_scenario.py <duration> <trigger text> <delay_s> [speed] [answer ...]
set STIMULUS=low_fuel for the low fuel button (default: danger)
"""
import os
import sys
KIND = os.environ.get("STIMULUS", "danger")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from case_study.scenario import Scenario, Stimulus, log_contains, run_scenario  # noqa: E402

duration, trigger, delay = float(sys.argv[1]), sys.argv[2], float(sys.argv[3])
speed = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
answers = sys.argv[5:]
sc = Scenario("danger", duration=duration, tcs_answers=answers,
              stimuli=[Stimulus(KIND, when=log_contains(trigger), delay=delay)])
print(run_scenario(sc, speed=speed).event_log.as_text())
