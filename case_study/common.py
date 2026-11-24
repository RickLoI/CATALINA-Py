"""Java: TCommon_Functions.

``Print``/``PrintLn`` append to the event log instead of the Swing ``Log_Memo``;
``Print_Colored_Text`` ignores the colour like Java does (the colour code is only recorded).
"""
from __future__ import annotations

from typing import Any, Dict, List

from catalina.model import Belief


class CommonFunctions:
    """Small helpers shared by the case-study functions: belief filtering by type/name and the ``print``
    family, which writes to the demo's event log instead of the Swing ``Log_Memo``.
    """
    def __init__(self, demo: Any):
        self.demo = demo

    def get_map_beliefs_by_type(self, beliefs: List[Belief], belief_type: str) -> Dict[str, Belief]:
        return {b.get_name(): b for b in beliefs if b.get_type_belief() == belief_type}

    def get_array_beliefs_by_type(self, beliefs: List[Belief], belief_type: str) -> List[Belief]:
        return [b for b in beliefs if b.get_type_belief() == belief_type]

    def get_beliefs_by_name(self, beliefs: List[Belief], belief_name: str) -> Dict[str, Belief]:
        return {b.get_name(): b for b in beliefs if b.get_name() == belief_name}

    def print_colored_text(self, text: Any, color: int) -> None:
        if text is None:
            text = ""
        self._emit(text, color)

    def print(self, text: Any) -> None:
        self.println(text)

    def println(self, text: Any) -> None:
        self._emit(text, None)

    def _emit(self, text: Any, color: Any) -> None:
        self.demo.event_log.emit("log", text=str(text), color=color)
