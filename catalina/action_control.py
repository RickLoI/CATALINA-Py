"""Action Control executive and action execution.

Java: TAction_Control, TAction_Execution.

``ActionControl`` is a thread whose loop only refreshes its copies of the uninhibited beliefs and
regions when an action is announced (``Updated_Action_to_Execute``); nobody announces it in the
case study. The real work is in ``ActionExecution.execute``: it looks up the function registered
for the action name (``register_plan_execution_funtion_to_execute``) and calls it with the
Global Workspace, the action and the beliefs, returning an ``ActionExecutionResult``. If no
function is registered it prints a warning and returns a result whose ``result`` is False.
"""
from __future__ import annotations

from typing import Any, Callable, Dict

from .agent_thread import AgentBaseThread
from .enums import TypeUpdateContract as C
from .handlers import ActionExecutionFunctionHandler, ActionExecutionResult


class ActionExecution:
    """Looks up and runs the function registered for an action name (Java: TAction_Execution)."""
    def __init__(self, owner: "ActionControl"):
        self.owner = owner
        self.plan_executive_function_handler = ActionExecutionFunctionHandler()
        self.plan_executive_function_handler.set_global_workspace(owner.global_workspace)

    def execute(self, active_action: Any, beliefs: Dict[str, Any]) -> ActionExecutionResult:
        return self.plan_executive_function_handler.execute_function_for_desire(active_action, beliefs)

    def register_plan_execution_funtion_to_execute(self, action_name: Any, func: Callable) -> None:
        self.plan_executive_function_handler.register_function(action_name, func)

    def register_plan_executioon_funtion_to_execute(self, action: Any, func: Callable) -> None:
        self.register_plan_execution_funtion_to_execute(action.get_action_name(), func)

    def unregister_plan_execution_function_to_execute(self, action_name: str) -> bool:
        return self.plan_executive_function_handler.unregister_function(action_name)


class ActionControl(AgentBaseThread):
    """Action Control thread (Java: TAction_Control): keeps fresh copies of beliefs/regions and exposes the
    registration API of the action functions.
    """
    def __init__(self, agent: Any):
        super().__init__(agent, "Action Control")
        self.owner = agent
        self.global_workspace = agent.get_global_workspace()
        self.result = False
        self.map_beliefs: Dict[str, Any] = {}
        self.map_regions: Dict[str, Any] = {}
        self.action_execution = ActionExecution(self)

    def insert_in_list_update_contract(self) -> None:
        gw = self.agent.get_global_workspace()
        for contract in (C.Updated_Action_to_Execute, C.Updated_Uninhibited_Data, C.Updated_Beliefs):
            gw.insert_for_update_contract(contract, self)

    def execute(self) -> None:
        mh = self.message_handler
        if mh.read_value_and_clear("action_to_execute"):
            updated_data = mh.read_value_and_clear("uninhibited_data")
            updated_beliefs = mh.read_value_and_clear("beliefs")
            if updated_data or updated_beliefs:
                self.map_beliefs = dict(self.global_workspace.get_map_uninhibited_beliefs())
                self.map_regions = dict(self.global_workspace.get_map_uninhibited_regions())

    def register_plan_execution_funtion_to_execute(self, action_name: str, func: Callable) -> None:
        self.action_execution.register_plan_execution_funtion_to_execute(action_name, func)

    def register_plan_executioon_funtion_to_execute(self, action: Any, func: Callable) -> None:
        self.action_execution.register_plan_executioon_funtion_to_execute(action, func)

    def unregister_plan_execution_function_to_execute(self, action_name: str) -> bool:
        return self.action_execution.unregister_plan_execution_function_to_execute(action_name)

    def get_action_execution(self) -> ActionExecution:
        return self.action_execution
