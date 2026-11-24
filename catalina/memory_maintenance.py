"""Memory-maintenance helpers that sit between the Global Workspace and the Long Memory.

Java: TLong_Term_Memory_Maintenance, TGW_Memory_Maintenance_Update_Belief_Function_Result,
TGlobal_Workspace_Memory_Maintenance_Update_Belief_Function_Handler,
TGlobal_Workspace_Memory_Maintenance.

The executive function itself (``TExecutive_Memory_Maintenance_Function``, a thread) is Phase 4.
Here ``owner`` is only stored.
"""
from __future__ import annotations

import sys
from typing import Any, Callable, Dict, List, Optional

from .long_memory import LongMemory


class LongTermMemoryMaintenance:
    """Java: TLong_Term_Memory_Maintenance (thin facade over the Long Memory)."""

    def __init__(self, owner: Any, long_memory: LongMemory):
        self.parent = owner
        self.long_memory = long_memory

    def get_attentional_desires(self):
        return self.long_memory.get_all_attentional_desires()

    def get_all_not_satisfied_attentional_desires(self):
        return self.long_memory.get_all_not_satisfied_attentional_desires()

    def get_inhibited_attentional_desires(self):
        return self.long_memory.get_inhibited_attentional_desires()

    def get_all_beliefs(self):
        return self.long_memory.get_all_beliefs()

    def get_all_map_beliefs(self):
        return self.long_memory.get_all_map_beliefs()

    def get_inhibited_beliefs(self):
        return self.long_memory.get_inhibited_beliefs()

    def set_beliefs(self, beliefs) -> None:
        self.long_memory.clear_beliefs()
        self.long_memory.add_beliefs(beliefs)

    def set_inhibited_data(self, inhibited_desires, inhibited_beliefs, inhibited_regions) -> None:
        self.long_memory.set_inhibited_data(inhibited_desires, inhibited_beliefs, inhibited_regions)

    def add_attentional_desires(self, desires) -> None:
        self.long_memory.add_attentional_desires(desires)

    def add_inhibited_practical_desires(self, desires_data) -> None:
        self.long_memory.add_inhibited_practical_desires(desires_data)   # Phase 4

    def add_satisfied_attentional_desires(self, desires) -> None:
        self.long_memory.add_satisfied_attentional_desires(desires)

    def remove_attentional_desires(self, desires) -> None:
        self.long_memory.remove_attentional_desires(desires)

    def get_regions(self):
        return self.long_memory.get_all_regions()

    def get_inhibited_regions(self):
        return self.long_memory.get_inhibited_regions()

    def remove_inhibited_data(self, inhibited_desires, inhibited_beliefs, inhibited_regions) -> None:
        self.long_memory.remove_inhibited_data(inhibited_desires, inhibited_beliefs, inhibited_regions)

    def add_inhibited_desire(self, inhibited_desires) -> None:
        self.long_memory.add_inhibited_desire(inhibited_desires)

    def get_all_green_desires(self):
        return self.long_memory.get_all_green_desires()

    def get_green_desires_by_names(self, names):
        return self.long_memory.get_green_desires_by_names(names)

    def get_all_quality_desires(self):
        return self.long_memory.get_all_quality_desires()

    def get_quality_desires_by_names(self, names):
        return self.long_memory.get_quality_desires_by_names(names)

    def get_satisfied_attentional_desires(self):
        return self.long_memory.get_all_satisfied_attentional_desires()

    def get_selected_beliefs(self, names):
        return self.long_memory.get_selected_beliefs(names)

    def get_selected_regions(self, names):
        return self.long_memory.get_selected_regions(names)

    def get_all_map_regions(self):
        return self.long_memory.get_all_map_regions()


class UpdateBeliefFunctionResult:
    """Java: TGW_Memory_Maintenance_Update_Belief_Function_Result."""

    def __init__(self) -> None:
        self.result: bool = False
        self.beliefs_to_change: Dict[str, Any] = {}

    def set_result(self, value: bool) -> None:
        self.result = value

    def get_result(self) -> bool:
        return self.result

    def clear(self) -> None:
        self.result = False
        self.beliefs_to_change.clear()

    def set_beliefs_to_change(self, values: Optional[Dict[str, Any]]) -> None:
        self.beliefs_to_change.clear()
        if values is not None:
            self.beliefs_to_change.update(values)

    def get_beliefs_to_change(self) -> Dict[str, Any]:
        return dict(self.beliefs_to_change)   # a copy, like Java


class UpdateBeliefFunctionHandler:
    """Java: TGlobal_Workspace_Memory_Maintenance_Update_Belief_Function_Handler.

    A registered function has the signature ``func(stimulus, beliefs: dict, recall_belief)``
    and returns an ``UpdateBeliefFunctionResult`` (or None).
    """

    def __init__(self) -> None:
        self.registered_functions: Dict[str, Callable] = {}
        self.recall_belief: Optional[Callable] = None

    def register_function(self, stimulus_type: Optional[str], func: Optional[Callable]) -> None:
        if stimulus_type is None or stimulus_type.strip() == "" or func is None:
            raise ValueError("Invalid Sensor or function for registration.")
        self.registered_functions[stimulus_type] = func

    def unregister_function(self, stimulus_type: Optional[str]) -> bool:
        if stimulus_type is None or stimulus_type.strip() == "":
            return False
        return self.registered_functions.pop(stimulus_type, None) is not None

    def execute_function_for_update_belief(self, stimulus, beliefs: Dict[str, Any]) -> UpdateBeliefFunctionResult:
        """Run the update-belief function registered for the stimulus type, passing the beliefs and the belief-
        recall callback; returns an empty result if there is none.
        """
        result = UpdateBeliefFunctionResult()
        if stimulus is None or stimulus.get_type_belief().strip() == "":
            print("Error: the Stimulus provided for execution is null.", file=sys.stderr)
            return result
        func = self.registered_functions.get(stimulus.get_type_belief())
        if func is not None:
            temp = func(stimulus, beliefs, self.recall_belief)
            if temp is not None:
                result = temp
        return result

    def set_recall_belief(self, func: Optional[Callable]) -> None:
        if func is not None:
            self.recall_belief = func


class GlobalWorkspaceMemoryMaintenance:
    """Java: TGlobal_Workspace_Memory_Maintenance."""

    def __init__(self, owner: Any, global_workspace: Any):
        self.parent = owner
        self.global_workspace = global_workspace
        self.update_normal_belief_function_handler = UpdateBeliefFunctionHandler()
        self.update_normal_belief_function_handler.set_recall_belief(global_workspace.recal_beliefs)
        self.update_critical_belief_function_handler = UpdateBeliefFunctionHandler()
        self.update_critical_belief_function_handler.set_recall_belief(global_workspace.recal_beliefs)

    def set_stimuli_in_gw(self, stimuli: List[Any]) -> None:
        """Updates uninhibited/important beliefs through the registered per-stimulus-type
        functions, broadcasts the changes, then publishes the stimuli."""
        gw = self.global_workspace
        updated_beliefs = False
        updated_critical_beliefs = False
        map_beliefs: Dict[str, Any] = dict(gw.get_map_uninhibited_beliefs())
        important_beliefs = list(gw.get_important_beliefs())
        for belief in important_beliefs:
            map_beliefs.pop(belief.get_name(), None)
        map_important_beliefs = {b.get_name(): b for b in important_beliefs}

        for stimulus in stimuli:
            temp = self.update_normal_belief_function_handler.execute_function_for_update_belief(
                stimulus, map_beliefs)
            updated_beliefs = updated_beliefs | temp.get_result()
            changes = temp.get_beliefs_to_change()
            if len(changes) > 0:
                gw.update_uninhibited_conscious_beliefs(changes)

            temp_critical = self.update_critical_belief_function_handler.execute_function_for_update_belief(
                stimulus, map_important_beliefs)
            changes = temp_critical.get_beliefs_to_change()
            if len(changes) > 0:
                gw.update_uninhibited_conscious_beliefs(changes)
            updated_critical_beliefs = updated_critical_beliefs | temp_critical.get_result()

        from .enums import TypeUpdateContract
        if updated_beliefs:
            gw.broadcast_signal(TypeUpdateContract.Updated_Beliefs)
        if updated_critical_beliefs:
            gw.broadcast_signal(TypeUpdateContract.Updated_Critical_Beliefs)
        gw.set_stimuli(stimuli)

    def register_update_beliefs_function(self, stimulus_type: str, func: Callable) -> None:
        self.update_normal_belief_function_handler.register_function(stimulus_type, func)

    def unregister_update_beliefs_function(self, stimulus_type: str) -> bool:
        return self.update_normal_belief_function_handler.unregister_function(stimulus_type)

    def add_uninhibited_preconditions(self, pre_conditions) -> None:
        self.global_workspace.add_uninhibited_preconditions(pre_conditions)

    def associate_functions_to_inhibited_desires(self, desires_data) -> None:
        self.global_workspace.associate_functions_to_inhibited_desires(desires_data)
