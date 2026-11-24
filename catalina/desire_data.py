"""Bundles used when desires are promoted/inhibited.

Java: TDesire_Data, TPractical_Desire_Data.

``DesireData`` getters return a list AND empty the internal set (Java behaviour): reading twice
gives the data once. Sets keep insertion order (Java HashSet order is arbitrary).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Set


class DesireData:
    """Java: TDesire_Data."""

    def __init__(self) -> None:
        self.preconditions: Dict[Any, None] = {}
        self.beliefs: Dict[Any, None] = {}
        self.regions: Dict[Any, None] = {}

    def clear(self) -> None:
        self.preconditions.clear()
        self.beliefs.clear()
        self.regions.clear()

    def get_preconditions(self) -> List[Any]:
        result = list(self.preconditions)
        self.preconditions.clear()
        return result

    def get_beliefs(self) -> List[Any]:
        result = list(self.beliefs)
        self.beliefs.clear()
        return result

    def get_regions(self) -> List[Any]:
        result = list(self.regions)
        self.regions.clear()
        return result

    def set_preconditions(self, values: Iterable[Any]) -> None:
        self.preconditions.clear()
        self.preconditions.update(dict.fromkeys(values))

    def set_beliefs(self, values: Iterable[Any]) -> None:
        self.beliefs.clear()
        self.beliefs.update(dict.fromkeys(values))

    def set_regions(self, values: Iterable[Any]) -> None:
        self.regions.clear()
        self.regions.update(dict.fromkeys(values))


class PracticalDesireData:
    """Java: TPractical_Desire_Data (a practical desire plus the functions tied to it)."""

    def __init__(self) -> None:
        self.practical_desire: Any = None
        self.associated_preconditions: Set[str] = set()
        self.associated_beliefs_inhibition_functions: Dict[Callable, None] = {}
        self.associated_regions_inhibition_functions: Dict[Callable, None] = {}
        self.associated_means_end_reasoner_function: Optional[Callable] = None

    def clear(self) -> None:
        self.practical_desire = None
        self.associated_preconditions.clear()
        self.associated_beliefs_inhibition_functions.clear()
        self.associated_regions_inhibition_functions.clear()

    def get_practical_desire(self) -> Any:
        return self.practical_desire

    def get_preconditions(self) -> Set[str]:
        return self.associated_preconditions

    def get_beliefs_inhibition_functions(self) -> List[Callable]:
        return list(self.associated_beliefs_inhibition_functions)

    def get_regions_inhibition_functions(self) -> List[Callable]:
        return list(self.associated_regions_inhibition_functions)

    def set_practical_desire(self, desire: Any) -> None:
        self.practical_desire = desire

    def set_preconditions_functions(self, preconditions: Optional[Iterable[str]]) -> None:
        self.associated_preconditions.clear()
        if preconditions:
            self.associated_preconditions.update(preconditions)

    def add_preconditions(self, preconditions: Optional[Iterable[str]]) -> None:
        if preconditions is not None:
            self.associated_preconditions.update(preconditions)

    def add_beliefs_inhibition_functions(self, func: Optional[Callable]) -> None:
        if func is not None:
            self.associated_beliefs_inhibition_functions[func] = None

    def add_regions_inhibition_functions(self, func: Optional[Callable]) -> None:
        if func is not None:
            self.associated_regions_inhibition_functions[func] = None

    def set_beliefs_functions(self, funcs: Iterable[Callable]) -> None:
        self.associated_beliefs_inhibition_functions.clear()
        self.associated_beliefs_inhibition_functions.update(dict.fromkeys(funcs))

    def set_regions_functions(self, funcs: Iterable[Callable]) -> None:
        self.associated_regions_inhibition_functions.clear()
        self.associated_regions_inhibition_functions.update(dict.fromkeys(funcs))

    def set_means_end_reasoner_function(self, func: Optional[Callable]) -> None:
        self.associated_means_end_reasoner_function = func

    def get_means_end_reasoner_function(self) -> Optional[Callable]:
        return self.associated_means_end_reasoner_function
