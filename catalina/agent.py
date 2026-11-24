"""The agent: wires Long Memory, Global Workspace and the executive functions.

Java: TAgent (constructor ``TAgent(String data_dir)``), TAgent_Status.

Construction order is the Java one (it fixes the order in which executives subscribe to the
Global Workspace update contracts, which matters for the "first subscriber" quirk, README 10):
long memory -> global workspace -> attention modulation -> desire handler -> reasoner ->
inhibition -> resource allocation -> action control -> switching -> perception -> memory
maintenance -> ``acquire_agent_components`` of long memory and of the Global Workspace.

The executives are threads created in "not started" state. ``start_executives`` starts the ones
that the case study starts (``Start_AV``: all except resource allocation and action control) and
``stop_executives`` ends them (extension; Java ends with ``System.exit``).

The ``reasoner_register_*``, ``inhibition_register_*`` methods are the Java delegating methods.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Callable, List, Optional

from .action_control import ActionControl
from .clock import REAL_CLOCK
from .executive_attention import AttentionSelection
from .executive_desires import DesireHandler
from .executive_inhibition import ExecutiveInhibitionFunction
from .executive_memory import ExecutiveMemoryMaintenanceFunction
from .executive_perception import ExecutivePerceptionFunction
from .executive_reasoner import ExecutiveReasonerFunction
from .executive_resources import ExecutiveResourceAllocationFunction
from .executive_switching import ExecutiveSwitchingFunction
from .global_workspace import GlobalWorkspace
from .long_memory import LongMemory


class AgentStatus(Enum):
    """Lifecycle flag of the agent."""
    Not_Active = "Not_Active"
    Active = "Active"


class Agent:
    """The CATALINA agent: owns the long-term memory, the Global Workspace and the executive-function threads.

    Java: TAgent. ``data_dir`` is the folder with the XML files (see ``LongMemory.initialize``). ``clock``
    is the object every executive uses to wait (``REAL_CLOCK`` or a ``SimClock``). ``bug_compatible`` keeps
    the Java loader quirks. Nothing runs until the threads are started (``Start_AV`` in the case study).
    """
    def __init__(self, data_dir: Optional[str] = None, bug_compatible: bool = True, clock: Any = None):
        print("Agent: Initialization...")
        self.clock = clock if clock is not None else REAL_CLOCK   # every executive wait goes through it
        self.status = AgentStatus.Not_Active
        self.long_memory = LongMemory(self, bug_compatible=bug_compatible)
        if data_dir is not None:
            self.long_memory.initialize(data_dir)
        self.global_workspace = GlobalWorkspace(self)
        self.attention_selection_component = AttentionSelection(self)
        self.desire_handler_component = DesireHandler(self)
        self.exec_reasoner = ExecutiveReasonerFunction(self)
        self.exec_inhibition_func = ExecutiveInhibitionFunction(self)
        self.exec_resource_allocation_func = ExecutiveResourceAllocationFunction(self)
        self.action_control = ActionControl(self)
        self.exec_switching_func = ExecutiveSwitchingFunction(self)
        self.exec_perception_func = ExecutivePerceptionFunction(self)
        self.exec_memory_maint_func = ExecutiveMemoryMaintenanceFunction(self, self.long_memory)
        self.long_memory.acquire_agent_components()
        self.global_workspace.acquire_agent_components()

    # ---- executives as threads
    def executives(self) -> List[Any]:
        return [self.desire_handler_component, self.attention_selection_component,
                self.exec_inhibition_func, self.exec_perception_func,
                self.exec_memory_maint_func, self.exec_reasoner, self.exec_switching_func]

    def all_threads(self) -> List[Any]:
        return self.executives() + [self.exec_resource_allocation_func, self.action_control]

    def stop_executives(self) -> None:
        for thread in self.all_threads():
            thread.stop()
        for thread in self.all_threads():
            if thread.is_alive():
                thread.join(timeout=2.0)

    def resume_executive_function(self, executive: Any) -> None:
        executive.resume()

    def suspend_executive_function(self, executive: Any) -> None:
        executive.suspend()

    # ---- getters (Java names in snake_case)
    def get_global_workspace(self) -> GlobalWorkspace:
        return self.global_workspace

    def get_long_memory(self) -> LongMemory:
        return self.long_memory

    def get_executive_perception_function(self) -> ExecutivePerceptionFunction:
        return self.exec_perception_func

    def get_executive_memory_maintenance_function(self) -> ExecutiveMemoryMaintenanceFunction:
        return self.exec_memory_maint_func

    def get_attention_modulation_component(self) -> AttentionSelection:
        return self.attention_selection_component

    def get_action_control(self) -> ActionControl:
        return self.action_control

    def get_desire_handler_component(self) -> DesireHandler:
        return self.desire_handler_component

    def get_executive_inhibition_function(self) -> ExecutiveInhibitionFunction:
        return self.exec_inhibition_func

    def get_executive_switching_function(self) -> ExecutiveSwitchingFunction:
        return self.exec_switching_func

    def get_executive_reasoner_function(self) -> ExecutiveReasonerFunction:
        return self.exec_reasoner

    def get_executive_resource_allocation_function(self) -> ExecutiveResourceAllocationFunction:
        return self.exec_resource_allocation_func

    def get_current_attentional_desires(self) -> List[Any]:
        return list(self.long_memory.get_all_attentional_desires())

    # ---- delegating registrations (Java: Reasoner_*, Inhibition_*)
    def reasoner_register_beliefs_names_for_desires(self, desire_name: str, beliefs_names) -> None:
        self.exec_reasoner.register_list_beliefs_names_for_desires(desire_name, beliefs_names)

    def reasoner_register_list_regions_names_for_desires(self, desire_name: str, regions_names) -> None:
        self.exec_reasoner.register_list_regions_names_for_desires(desire_name, regions_names)

    def reasoner_register_epistemic_function(self, belief_type: str, func: Callable) -> None:
        self.exec_reasoner.register_epistemic_function(belief_type, func)

    def reasoner_unregister_epistemic_function(self, belief_type: str) -> bool:
        return self.exec_reasoner.unregister_epistemic_function(belief_type)

    def reasoner_register_practical_function(self, desire_name: str, func: Callable) -> None:
        self.exec_reasoner.register_practical_function(desire_name, func)

    def reasoner_unregister_practical_function(self, desire_name: str) -> bool:
        return self.exec_reasoner.unregister_practical_function(desire_name)

    def inhibition_register_practical_belief_inhibition_function(self, desire_name: str, func: Callable) -> None:
        self.exec_inhibition_func.register_practical_belief_inhibition_function(desire_name, func)

    def inhibition_unregister_practical_belief_inhibition_function(self, desire_name: str) -> bool:
        return self.exec_inhibition_func.unregister_practical_belief_inhibition_function(desire_name)

    def inhibition_register_epistemic_belief_inhibition_function(self, desire_name: str, func: Callable) -> None:
        self.exec_inhibition_func.register_epistemic_belief_inhibition_function(desire_name, func)

    def inhibition_unregister_epistemic_belief_inhibition_function(self, desire_name: str) -> bool:
        return self.exec_inhibition_func.unregister_epistemic_belief_inhibition_function(desire_name)

    def inhibition_register_practical_region_function(self, name: str, func: Callable) -> None:
        self.exec_inhibition_func.register_practical_region_inhibition_function(name, func)

    def inhibition_unregister_practical_region_function(self, name: str) -> bool:
        return self.exec_inhibition_func.unregister_practical_region_inhibition_function(name)

    def inhibition_register_epistemic_region_function(self, name: str, func: Callable) -> None:
        self.exec_inhibition_func.register_epistemic_region_inhibition_function(name, func)

    def inhibition_unregister_epistemic_region_function(self, name: str) -> bool:
        return self.exec_inhibition_func.unregister_epistemic_region_inhibition_function(name)
