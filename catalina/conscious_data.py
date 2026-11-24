"""Java: TConscious_Data (the four sets: pre-conditions, beliefs, attentional desires, regions).

Only the API used so far is ported (``read_*``, ``write``, ``add_data``). Sets keep insertion
order (Java HashSet order is arbitrary). ``Quadruple`` mirrors TQuadruple_Object.
"""
from __future__ import annotations

import threading
from typing import Any, List, Optional


class Quadruple:
    """Java: TQuadruple_Object."""

    def __init__(self, first: Any = None, second: Any = None, third: Any = None, fourth: Any = None):
        self.object_first = first
        self.object_second = second
        self.object_third = third
        self.object_fourth = fourth

    def get_object_first(self) -> Any:
        return self.object_first

    def get_object_second(self) -> Any:
        return self.object_second

    def get_object_third(self) -> Any:
        return self.object_third

    def get_object_fourth(self) -> Any:
        return self.object_fourth


def _unique(items) -> dict:
    return dict.fromkeys(items)


class ConsciousData:
    """Thread-safe container of what is currently 'conscious' in the Global Workspace: preconditions, beliefs,
    attentional desires and regions (Java: TConscious_Data).
    """
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.pre_conditions: dict = {}
        self.beliefs: dict = {}
        self.attentional_desires: dict = {}
        self.regions: dict = {}

    def read(self) -> Quadruple:
        with self._lock:
            return Quadruple(self.pre_conditions, self.beliefs, self.attentional_desires, self.regions)

    def read_beliefs(self) -> List[Any]:
        with self._lock:
            return list(self.beliefs)

    def read_pre_conditions(self) -> List[Any]:
        with self._lock:
            return list(self.pre_conditions)

    def read_attentional_desires(self) -> List[Any]:
        with self._lock:
            return list(self.attentional_desires)

    def read_regions(self) -> List[Any]:
        with self._lock:
            return list(self.regions)

    def write(self, pre_conditions: Optional[List[Any]], beliefs: List[Any],
              attentional_desires: List[Any], regions: List[Any]) -> None:
        """Java: Write(ArrayList x4). ``pre_conditions=None`` leaves the old pre-conditions."""
        with self._lock:
            if pre_conditions is not None:
                self.pre_conditions = _unique(pre_conditions)
            self.beliefs = _unique(beliefs)
            self.attentional_desires = _unique(attentional_desires)
            self.regions = _unique(regions)

    def add_data(self, pre_conditions: List[Any], beliefs: List[Any],
                 attentional_desires: List[Any], regions: List[Any]) -> None:
        with self._lock:
            self.pre_conditions.update(_unique(pre_conditions))
            self.beliefs.update(_unique(beliefs))
            self.attentional_desires.update(_unique(attentional_desires))
            self.regions.update(_unique(regions))
