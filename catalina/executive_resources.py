"""Executive Resource Allocation Function.

Java: TExecutive_Resource_Allocation_Function, TResource_Managment.

For every critical (important) belief that is not a final state of a selected intention, the
function registered for the belief type may create practical desires and ask the switching
executive to abort options (internal signal). The case study does NOT start this executive
(``Start_AV`` leaves it out).

Deviation: Java's ``Execute`` contains its own ``while (Read_Continue_Thread())`` busy loop, so the
outer 50 ms loop never takes control back; here one pass is done per ``execute`` call (the thread
loop provides the repetition, with the 50 ms sleep).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .agent_thread import AgentBaseThread
from .desires import EpistemicDesire, PracticalDesire
from .enums import TypeUpdateContract as C
from .handlers import ResourceManagmentPracticalFunctionsHandler


class ResourceManagment:
    """Runs the functions registered per critical-belief type and broadcasts the resulting abort-option
    internal signals.
    """
    def __init__(self, owner: Any, global_workspace: Any):
        self.parent = owner
        self.global_workspace = global_workspace
        self.practical_functions_handler = ResourceManagmentPracticalFunctionsHandler()
        self.new_practical_desires: List[Any] = []
        self.new_internal_signals: List[Any] = []
        self.new_data: List[Any] = []

    def execute(self, critical_beliefs: List[Any], uninhibited_beliefs: List[Any],
                selected_intentions: List[Any], selected_final_states: Dict[Any, None]) -> None:
        """For each critical belief that is not a final state of a selected intention, run its registered
        function and broadcast the signals it returns.
        """
        for belief in critical_beliefs:
            self.new_practical_desires = []
            self.new_internal_signals = []
            self.new_data = []
            if belief not in selected_final_states:
                results = self.practical_functions_handler.execute_function_for_desire(
                    belief, uninhibited_beliefs, selected_intentions)
                self.new_practical_desires.append(results.get_object_first())
                self.new_internal_signals.append(results.get_object_second())
                self.new_data.extend(results.get_object_third())
                self.global_workspace.broadcast_internal_signals_messages(
                    C.Internal_Signals_Abort_Option, self.parent.name, list(self.new_data))

    def add_funtion_to_belief(self, type_stimulus: Any, func: Callable) -> None:
        if not isinstance(type_stimulus, str):
            type_stimulus = type_stimulus.get_type_belief()
        self.practical_functions_handler.register_function(type_stimulus, func)

    def remove_funtion_to_belief(self, type_stimulus: Any) -> None:
        if not isinstance(type_stimulus, str):
            type_stimulus = type_stimulus.get_type_belief()
        self.practical_functions_handler.unregister_function(type_stimulus)


class ExecutiveResourceAllocationFunction(AgentBaseThread):
    """Executive Resource Allocation thread (not started by the case study)."""
    def __init__(self, agent: Any):
        super().__init__(agent, "Executive Resource Allocation Function")
        self.global_workspace = agent.get_global_workspace()
        self.resource_managment = ResourceManagment(self, self.global_workspace)
        self.critical_beliefs: List[Any] = []
        self.uninhibited_beliefs: List[Any] = []
        self.selected_intentions: List[Any] = []
        self.selected_final_states: Dict[Any, None] = {}

    def insert_in_list_update_contract(self) -> None:
        gw = self.agent.get_global_workspace()
        for contract in (C.Updated_Beliefs, C.Updated_Uninhibited_Data, C.Updated_Selected_Intentions,
                         C.Updated_Critical_Beliefs):
            gw.insert_for_update_contract(contract, self)

    def execute(self) -> None:
        """Refresh critical beliefs, uninhibited beliefs and the final states of the selected intentions, then
        run one resource-management pass.
        """
        mh = self.message_handler
        gw = self.global_workspace
        self.critical_beliefs = list(gw.get_important_beliefs())
        if mh.read_value_and_clear("beliefs") or mh.read_value_and_clear("uninhibited_data"):
            self.uninhibited_beliefs = list(gw.get_uninhibited_beliefs())
        if mh.read_value_and_clear("selected_intentions"):
            self.selected_intentions = list(gw.get_selected_intentions())
            self.selected_final_states = {}
            for intention in self.selected_intentions:
                desire = intention.get_active_desire()
                if isinstance(desire, PracticalDesire):
                    self.selected_final_states.update(dict.fromkeys(desire.get_final_state().get_beliefs()))
                elif isinstance(desire, EpistemicDesire):
                    self.selected_final_states[desire.get_belief()] = None
                else:
                    raise ValueError(f"Unexpected value: {desire}")
        self.resource_managment.execute(self.critical_beliefs, self.uninhibited_beliefs,
                                        self.selected_intentions, self.selected_final_states)

    def add_funtion_to_belief(self, type_stimulus: Any, func: Callable) -> None:
        self.resource_managment.add_funtion_to_belief(type_stimulus, func)

    def remove_funtion_to_belief(self, type_stimulus: Any) -> None:
        self.resource_managment.remove_funtion_to_belief(type_stimulus)

    def get_global_workspace(self) -> Any:
        return self.global_workspace

    def load_importan_beliefs(self) -> None:
        pass
