"""Executive Inhibition Function.

Java: TExecutive_Inhibition_Function, TBelief_Inhibition, TDesires_Inhibition, TRegions_Inhibition.

Whenever thresholds change, and with the selected intentions in hand, the executive decides what
stays "conscious" (uninhibited) in the Global Workspace: the beliefs/regions related to the
intentions (through the inhibition functions registered by desire name / belief type), the
pre-conditions of the practical desires and the always-consider (critical) beliefs. The rest is
inhibited. Without selected intentions everything is inhibited and the not-satisfied desires go
back to standing.

Java behaviour kept on purpose:
* ``register_epistemic_region_inhibition_function`` does nothing (empty body in Java), so epistemic
  desires never uninhibit regions; the unregister variant does work.
* A critical belief name that is not in the memory map raises (Java: NullPointerException).
* The sets are insertion-ordered dicts here (Java HashSet, undefined order).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .agent_thread import AgentBaseThread
from .desires import EpistemicDesire, PracticalDesire
from .enums import TypeUpdateContract as C
from .handlers import BeliefInhibitionFunctionHandler, RegionInhibitionFunctionHandler
from .model import Belief


def _oset(items=()) -> Dict[Any, None]:
    return dict.fromkeys(items)


class BeliefInhibition:
    """Decides which beliefs stay uninhibited: those of the selected intentions (preconditions, registered
    functions), the always-consider (critical) ones; the others are inhibited.
    """
    def __init__(self, owner: "ExecutiveInhibitionFunction"):
        self.owner = owner
        self.global_workspace = owner.get_global_workspace()
        self.inhibited_beliefs: List[Any] = []
        self.uninhibited_beliefs: List[Any] = []
        self.pre_conditions: List[Any] = []
        self.list_beliefs_to_always_consider: Dict[str, List[str]] = {}
        self.practical_belief_inhibition_handler = BeliefInhibitionFunctionHandler()
        self.practical_precondition_inhibition_handler = BeliefInhibitionFunctionHandler()
        self.epistemic_belief_inhibition_handler = BeliefInhibitionFunctionHandler()

    def execute(self, selected_intentions: List[Any]) -> None:
        """Compute the uninhibited beliefs, the preconditions and the inhibited beliefs for the selected
        intentions (a belief name unknown to the memory raises, as in Java).
        """
        all_map_beliefs: Dict[str, Any] = dict(self.global_workspace.get_all_map_beliefs_from_mm())
        uninhibited = _oset()
        pre_conditions = _oset()
        for intention in selected_intentions:
            desire = intention.get_active_desire()
            if desire is None:
                continue
            if isinstance(desire, PracticalDesire):
                precondition_names: List[Optional[str]] = []
                if desire.get_trigger_condition() is not None:
                    precondition_names.extend(desire.get_trigger_condition().get_beliefs_names())
                if None in precondition_names:
                    precondition_names.remove(None)
                if len(precondition_names) > 0:
                    for name in precondition_names:
                        belief = all_map_beliefs.get(name)
                        if belief is not None:
                            pre_conditions[belief] = None
                    uninhibited.update(pre_conditions)
                names = self.practical_belief_inhibition_handler.execute_function_for_desire(
                    desire.get_name(), desire, all_map_beliefs)
                for name in names:
                    belief = all_map_beliefs.get(name)
                    if belief is not None:
                        uninhibited[belief] = None
            elif isinstance(desire, EpistemicDesire):
                uninhibited[desire.get_belief()] = None
                names = self.epistemic_belief_inhibition_handler.execute_function_for_desire(
                    desire.get_belief().get_type_belief(), desire, all_map_beliefs)
                for name in names:
                    belief = all_map_beliefs.get(name)
                    if belief is not None:
                        uninhibited[belief] = None
            else:
                raise ValueError(f"Unexpected value: {desire}")

        critical_types = _oset(self.owner.get_list_important_belief_type())
        critical_types.pop(None, None)
        always = _oset(critical_types)
        for list_name, beliefs in self.list_beliefs_to_always_consider.items():
            always.update(_oset(beliefs))
        for belief_name in always:
            belief = all_map_beliefs.get(belief_name)
            uninhibited[belief] = None
            if isinstance(belief.get_predicate().get_subject(), Belief):      # NPE if unknown, as Java
                uninhibited[belief.get_predicate().get_subject()] = None

        inhibited = [b for b in all_map_beliefs.values() if b not in uninhibited]
        self.inhibited_beliefs = list(_oset(inhibited))
        self.uninhibited_beliefs = list(uninhibited)
        self.pre_conditions = list(pre_conditions)

    def get_uninhibited_beliefs(self) -> List[Any]:
        result, self.uninhibited_beliefs = list(self.uninhibited_beliefs), []
        return result

    def get_inhibited_beliefs(self) -> List[Any]:
        result, self.inhibited_beliefs = list(self.inhibited_beliefs), []
        return result

    def get_pre_conditions(self) -> List[Any]:
        result, self.pre_conditions = list(self.pre_conditions), []
        return result

    def add_beliefs_to_always_consider(self, list_name: str, beliefs_names: List[str]) -> None:
        self.list_beliefs_to_always_consider[list_name] = beliefs_names

    def register_practical_belief_inhibition_function(self, name: str, func: Callable) -> None:
        self.practical_belief_inhibition_handler.register_belief_inhibition_function(name, func)

    def unregister_practical_belief_inhibition_function(self, name: str) -> bool:
        return self.practical_belief_inhibition_handler.unregister_belief_inhibition_function(name)

    def register_practical_preconditions_inhibition_function(self, name: str, func: Callable) -> None:
        self.practical_precondition_inhibition_handler.register_belief_inhibition_function(name, func)

    def unregister_practical_preconditions_inhibition_function(self, name: str) -> bool:
        return self.practical_precondition_inhibition_handler.unregister_belief_inhibition_function(name)

    def register_epistemic_belief_inhibition_function(self, name: str, func: Callable) -> None:
        self.epistemic_belief_inhibition_handler.register_belief_inhibition_function(name, func)

    def unregister_epistemic_belief_inhibition_function(self, name: str) -> bool:
        return self.epistemic_belief_inhibition_handler.unregister_belief_inhibition_function(name)


class DesiresInhibition:
    """Uninhibits the desires of the selected intentions and inhibits all the other attentional desires."""
    def __init__(self, owner: "ExecutiveInhibitionFunction"):
        self.parent = owner
        self.global_workspace = owner.get_global_workspace()
        self.inhibited_desires: List[Any] = []
        self.uninhibited_desires: List[Any] = []

    def execute(self, intentions: List[Any]) -> None:
        inhibited = _oset(self.global_workspace.get_attentional_desires())
        uninhibited = _oset(i.get_active_desire() for i in intentions)
        for d in uninhibited:
            inhibited.pop(d, None)
        self.uninhibited_desires = list(uninhibited)
        self.inhibited_desires = list(inhibited)

    def get_uninhibited_desires(self) -> List[Any]:
        result, self.uninhibited_desires = list(self.uninhibited_desires), []
        return result

    def get_inhibited_desires(self) -> List[Any]:
        result, self.inhibited_desires = list(self.inhibited_desires), []
        return result


class RegionsInhibition:
    """Uninhibits the regions returned by the registered functions for the desires of the selected intentions;
    all the other regions are inhibited.
    """
    def __init__(self, owner: "ExecutiveInhibitionFunction"):
        self.owner = owner
        self.global_workspace = owner.get_global_workspace()
        self.inhibited_regions: List[Any] = []
        self.uninhibited_regions: List[Any] = []
        self.practical_handler = RegionInhibitionFunctionHandler()
        self.epistemic_handler = RegionInhibitionFunctionHandler()
        self.generate_unhinibited_regions_for_intention: Optional[Callable] = None

    def execute(self, intentions: List[Any]) -> None:
        """Compute the uninhibited and inhibited regions for the given intentions using the registered
        practical/epistemic region functions.
        """
        self.uninhibited_regions = []
        self.inhibited_regions = []
        gw = self.global_workspace
        inhibited = _oset(gw.get_all_regions_from_mm())
        all_map_beliefs = dict(gw.get_all_map_beliefs_from_mm())
        all_map_regions = dict(gw.get_all_map_regions_from_ltm())
        names: List[Optional[str]] = []
        for intention in intentions:
            desire = intention.get_active_desire()
            if desire is None:
                continue
            if isinstance(desire, PracticalDesire):
                names.extend(self.practical_handler.execute_function_for_desire(
                    desire.get_name(), intention, all_map_beliefs, all_map_regions))
            elif isinstance(desire, EpistemicDesire):
                names.extend(self.epistemic_handler.execute_function_for_desire(
                    desire.get_belief().get_type_belief(), intention, all_map_beliefs, all_map_regions))
            else:
                raise ValueError(f"Unexpected value: {desire}")
        if None in names:
            names.remove(None)
        uninhibited = _oset(all_map_regions.get(n) for n in names)
        for r in uninhibited:
            inhibited.pop(r, None)
        self.inhibited_regions = list(inhibited)
        self.uninhibited_regions = list(uninhibited)

    def get_uninhibited_regions(self) -> List[Any]:
        result, self.uninhibited_regions = list(self.uninhibited_regions), []
        return result

    def get_inhibited_regions(self) -> List[Any]:
        result, self.inhibited_regions = list(self.inhibited_regions), []
        return result

    def set_generate_unhinibited_regions_for_intention(self, func: Optional[Callable]) -> None:
        self.generate_unhinibited_regions_for_intention = func

    def register_practical_region_inhibition_function(self, name: str, func: Callable) -> None:
        self.practical_handler.register_region_inhibition_function(name, func)

    def unregister_practical_region_inhibition_function(self, name: str) -> bool:
        return self.practical_handler.unregister_region_inhibition_function(name)

    def register_epistemic_region_inhibition_function(self, name: str, func: Callable) -> None:
        pass     # empty body in Java

    def unregister_epistemic_region_inhibition_function(self, name: str) -> bool:
        return self.epistemic_handler.unregister_region_inhibition_function(name)


class ExecutiveInhibitionFunction(AgentBaseThread):
    """Executive Inhibition thread: recomputes the conscious (uninhibited) data of the Global Workspace
    whenever the thresholds change.
    """
    def __init__(self, agent: Any):
        super().__init__(agent, "Executive Inhibition Function")
        self.global_workspace = agent.get_global_workspace()
        self.belief_inhibition = BeliefInhibition(self)
        self.desires_inhibition = DesiresInhibition(self)
        self.regions_inhibition = RegionsInhibition(self)
        self.selected_intentions: List[Any] = []
        self.list_important_belief_type: Dict[str, None] = {}

    def insert_in_list_update_contract(self) -> None:
        gw = self.agent.get_global_workspace()
        gw.insert_for_update_contract(C.Updated_Selected_Intentions, self)
        gw.insert_for_update_contract(C.Updated_Thresholds, self)

    def execute(self) -> None:
        """Runs only when a 'thresholds' update arrived. With selected intentions: belief, desire and region
        inhibition, then publish the inhibited/uninhibited data; without: everything inhibited and not-
        satisfied desires go back to Standing.
        """
        mh = self.message_handler
        gw = self.global_workspace
        if not mh.read_value_and_clear("thresholds"):
            return
        if mh.read_value_and_clear("selected_intentions"):
            self.selected_intentions = list(gw.get_selected_intentions())
        inhibited_beliefs: List[Any] = []
        uninhibited_beliefs: List[Any] = []
        pre_conditions: List[Any] = []
        inhibited_desires: List[Any] = []
        uninhibited_desires: List[Any] = []
        inhibited_regions: List[Any] = []
        uninhibited_regions: List[Any] = []
        if len(self.selected_intentions) > 0:
            self.belief_inhibition.execute(self.selected_intentions)
            uninhibited_beliefs.extend(self.belief_inhibition.get_uninhibited_beliefs())
            pre_conditions.extend(self.belief_inhibition.get_pre_conditions())
            inhibited_beliefs.extend(self.belief_inhibition.get_inhibited_beliefs())
            self.desires_inhibition.execute(self.selected_intentions)
            uninhibited_desires.extend(self.desires_inhibition.get_uninhibited_desires())
            inhibited_desires.extend(self.desires_inhibition.get_inhibited_desires())
            self.regions_inhibition.execute(self.selected_intentions)
            uninhibited_regions.extend(self.regions_inhibition.get_uninhibited_regions())
            inhibited_regions.extend(self.regions_inhibition.get_inhibited_regions())
        else:
            for desire in gw.get_all_practical_desires():
                pre_conditions.extend(desire.get_trigger_condition().get_beliefs())
            gw.mark_as_standing_desires(gw.get_all_not_satisfied_attentional_desire_from_mm())
            inhibited_desires.extend(gw.get_all_not_satisfied_attentional_desire_from_mm())
        gw.set_inhibited_conscious_data(inhibited_beliefs, inhibited_desires, inhibited_regions)
        gw.set_uninhibited_conscious_data(pre_conditions, uninhibited_beliefs, uninhibited_desires,
                                          uninhibited_regions)

    def add_important_belief_type(self, belief_type: str) -> None:
        self.list_important_belief_type[belief_type] = None

    def get_list_important_belief_type(self) -> List[str]:
        return list(self.list_important_belief_type)

    def clear_list_important_belief_type(self) -> None:
        self.list_important_belief_type.clear()

    def set_generate_unhinibited_regions_for_intention(self, func: Optional[Callable]) -> None:
        self.regions_inhibition.set_generate_unhinibited_regions_for_intention(func)

    def get_global_workspace(self) -> Any:
        return self.global_workspace

    def add_beliefs_to_always_consider(self, list_name: str, beliefs_names: List[str]) -> None:
        self.belief_inhibition.add_beliefs_to_always_consider(list_name, beliefs_names)

    def register_practical_preconditions_inhibition_function(self, name: str, func: Callable) -> None:
        self.belief_inhibition.register_practical_preconditions_inhibition_function(name, func)

    def unregister_practical_preconditions_inhibition_function(self, name: str) -> bool:
        return self.belief_inhibition.unregister_practical_preconditions_inhibition_function(name)

    def register_practical_belief_inhibition_function(self, name: str, func: Callable) -> None:
        self.belief_inhibition.register_practical_belief_inhibition_function(name, func)

    def unregister_practical_belief_inhibition_function(self, name: str) -> bool:
        return self.belief_inhibition.unregister_practical_belief_inhibition_function(name)

    def register_epistemic_belief_inhibition_function(self, name: str, func: Callable) -> None:
        self.belief_inhibition.register_epistemic_belief_inhibition_function(name, func)

    def unregister_epistemic_belief_inhibition_function(self, name: str) -> bool:
        return self.belief_inhibition.unregister_epistemic_belief_inhibition_function(name)

    def register_practical_region_inhibition_function(self, name: str, func: Callable) -> None:
        self.regions_inhibition.register_practical_region_inhibition_function(name, func)

    def unregister_practical_region_inhibition_function(self, name: str) -> bool:
        return self.regions_inhibition.unregister_practical_region_inhibition_function(name)

    def register_epistemic_region_inhibition_function(self, name: str, func: Callable) -> None:
        self.regions_inhibition.register_epistemic_region_inhibition_function(name, func)

    def unregister_epistemic_region_inhibition_function(self, name: str) -> bool:
        return self.regions_inhibition.unregister_epistemic_region_inhibition_function(name)
