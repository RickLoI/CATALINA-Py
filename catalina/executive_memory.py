"""Executive Working Memory Maintenance Function.

Java: TExecutive_Memory_Maintenance_Function. The two helpers (``GlobalWorkspaceMemoryMaintenance``,
``LongTermMemoryMaintenance``) live in ``memory_maintenance.py``.

Loop: when new filtered stimuli arrive, copy them and hand them to
``GlobalWorkspaceMemoryMaintenance.set_stimuli_in_gw`` (which updates beliefs and publishes the
stimuli). Thresholds are only tracked, they are not used (as in Java).
"""
from __future__ import annotations

from typing import Any, Callable, List

from .agent_thread import AgentBaseThread
from .enums import TypeUpdateContract as C
from .memory_maintenance import GlobalWorkspaceMemoryMaintenance, LongTermMemoryMaintenance


class ExecutiveMemoryMaintenanceFunction(AgentBaseThread):
    """Executive Working Memory Maintenance thread: turns the filtered stimuli into belief updates through
    ``GlobalWorkspaceMemoryMaintenance``.
    """
    def __init__(self, agent: Any, long_memory: Any):
        super().__init__(agent, "Executive Working Memory Maintenance Function")
        self.global_workspace = agent.get_global_workspace()
        self.global_workspace_memory_maintenance = GlobalWorkspaceMemoryMaintenance(
            self, self.agent.get_global_workspace())
        self.long_term_memory_maintenance = LongTermMemoryMaintenance(self, long_memory)
        self.filtered_stimuli: List[Any] = []
        self.saliency_threshold = 0.0
        self.attention_threshold = 0.0
        thresholds = self.agent.get_global_workspace().get_saliency_and_attention_thresholds()
        if thresholds is not None:
            self.saliency_threshold = thresholds.get_object_first()
            self.attention_threshold = thresholds.get_object_second()

    def insert_in_list_update_contract(self) -> None:
        gw = self.agent.get_global_workspace()
        gw.insert_for_update_contract(C.Updated_Filtered_Stimuli, self)
        gw.insert_for_update_contract(C.Updated_Thresholds, self)

    def execute(self) -> None:
        """When new filtered stimuli arrive, copy them (tracking the thresholds) and hand them to the GW memory
        maintenance.
        """
        mh = self.message_handler
        if mh.read_value_and_clear("filtered_stimuli"):
            self.filtered_stimuli = list(self.global_workspace.get_filtered_stimuli())
            if mh.read_value_and_clear("thresholds"):
                thresholds = self.agent.get_global_workspace().get_saliency_and_attention_thresholds()
                self.saliency_threshold = thresholds.get_object_first()
                self.attention_threshold = thresholds.get_object_second()
            if len(self.filtered_stimuli) > 0:
                self.global_workspace_memory_maintenance.set_stimuli_in_gw(self.filtered_stimuli)

    def get_gw_memory_maintenance(self) -> GlobalWorkspaceMemoryMaintenance:
        return self.global_workspace_memory_maintenance

    def get_lt_memory_maintenance(self) -> LongTermMemoryMaintenance:
        return self.long_term_memory_maintenance

    def register_update_beliefs_function(self, stimulus_type: str, func: Callable) -> None:
        self.global_workspace_memory_maintenance.register_update_beliefs_function(stimulus_type, func)

    def unregister_update_beliefs_function(self, stimulus_type: str) -> bool:
        return self.global_workspace_memory_maintenance.unregister_update_beliefs_function(stimulus_type)

    def add_uninhibited_preconditions(self, pre_conditions) -> None:
        self.global_workspace_memory_maintenance.add_uninhibited_preconditions(pre_conditions)

    def associate_functions_to_inhibited_desires(self, desires_data) -> None:
        self.global_workspace_memory_maintenance.associate_functions_to_inhibited_desires(desires_data)
