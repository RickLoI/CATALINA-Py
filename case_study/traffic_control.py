"""Traffic Control Service and Virtual GPS.

Java: TTrafficControlService, TVirtual_GPS.

``Danger_Query_Simulation`` is interactive in Java: it asks (in the log) the danger type and the
closing duration and waits for the GUI "Send" button (``Response_Sended`` / ``String_Response_Sended``).
Here the answers can come from

* ``scripted_answers`` (a queue of strings consumed in order: first the danger-type index,
  then the duration), used by headless scenarios, or
* ``submit_response(text)`` (what the Send button does), used by the GUI.

The waiting is done on an ``Event`` instead of a 100 ms polling loop, and stops when the demo is
stopping. The unused ``Random_Number`` of Java is not drawn.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Iterable, List, Optional

from .domain import TTypeDanger


class VirtualGPS:
    """Java: TVirtual_GPS (not registered with the agent: sensor 'GPS' is ignored, see README)."""

    def __init__(self, agent: Any):
        self.agent = agent
        self.positions: List[int] = []

    def set_current_position(self, city: int, route: int, step: int) -> None:
        self.positions.extend([city, route, step])

    def get_current_position(self) -> List[int]:
        result = list(self.positions)
        self.positions.clear()
        return result


class TrafficControlService:
    """Virtual traffic control (Java: TTrafficControlService): when the car meets a closed route it asks why
    and for how long, and builds the danger data. Answers come from ``scripted_answers`` or from
    ``submit_response``.
    """
    def __init__(self, demo: Any, scripted_answers: Optional[Iterable[str]] = None):
        self.demo = demo
        self.common_functions = demo.common_functions
        self.danger_data: List[int] = []
        self.new_data_acquired = False
        self.response_sended = False
        self.string_response_sended = ""
        self.value_for_sample_execution = True
        self.scripted_answers: Deque[str] = deque(scripted_answers or [])
        self._response_event = threading.Event()

    # ---- answers
    def submit_response(self, text: str) -> None:
        """GUI 'Send' button: ``String_Response_Sended = text; Response_Sended = true``."""
        self.string_response_sended = text
        self.response_sended = True
        self._response_event.set()

    def _wait_answer(self) -> Optional[str]:
        """Next answer: from the scripted queue if any, otherwise wait (polling every 0.1 s) for
        ``submit_response``; None when the demo is stopping.
        """
        if self.scripted_answers:
            return self.scripted_answers.popleft()
        while not self.response_sended:
            if self.demo.stopping.is_set():
                return None
            self._response_event.wait(0.1)
        self._response_event.clear()
        self.response_sended = False
        answer = self.string_response_sended
        self.string_response_sended = ""
        return answer

    # ---- Java Danger_Query_Simulation
    def danger_query_simulation(self, real_positions: List[int]) -> None:
        """Ask the two questions (danger type, duration in 15-minute slots), repeating a question on a wrong
        answer, then store the danger data.
        """
        cf = self.common_functions
        city_position, route_position, step_position, dangerous_route = (
            real_positions[0], real_positions[1], real_positions[2], real_positions[3])
        cf.print_colored_text("- Why is the route closed?", 2)
        question = ""
        for counter, type_danger in enumerate(TTypeDanger.values()):
            question += f"{counter}- {type_danger}\n"
        if len(question) > 0:
            question = question[:-1]
        index = -1
        while True:
            cf.print_colored_text(question, 2)
            answer = self._wait_answer()
            if answer is None:
                return
            cf.print(" Your response was: " + answer)
            repeat = True
            if answer != "":
                try:
                    index = int(answer)
                    repeat = not (0 <= index < len(TTypeDanger.values()))
                except ValueError:
                    repeat = True
            if repeat:
                cf.print_colored_text("The Answer was wrong! Repeat please.", 2)
            else:
                break
        type_danger = TTypeDanger.values()[index]
        minimum, maximum = 1, 100
        question = ("\n- How long will the route be closed?\n"
                    "Enter the number of time slots as an integer between 1 and 100.(a time slot equals 15 minutes)")
        while True:
            cf.print_colored_text(question, 2)
            answer = self._wait_answer()
            if answer is None:
                return
            cf.print(" Your response was: " + answer)
            repeat = True
            if answer != "":
                try:
                    index = int(answer)
                    repeat = not (minimum <= index <= maximum)
                except ValueError:
                    repeat = True
            if repeat:
                cf.print_colored_text("The Answer was wrong! Repeat please.", 2)
            else:
                break
        duration = index
        self.danger_data.clear()
        # Danger_Data: 0 City, 1 Route, 2 Step, 3 Dangerous route, 4 Type_Danger.ordinal(), 5 Duration
        self.danger_data.extend([city_position, route_position, step_position, dangerous_route,
                                 type_danger.ordinal, duration])
        self.new_data_acquired = self.value_for_sample_execution

    def get_danger_data(self) -> List[int]:
        result: List[int] = []
        if self.new_data_acquired:
            self.new_data_acquired = False
            result.extend(self.danger_data)
            self.danger_data.clear()
        return result
