"""Executive Switching Function (+ option advancement evaluation and option execution).

Java: TExecutive_Switching_Function, TOption_Advancement_Evaluation, TOption_Execution.

The switching executive drives the plan of the first selected intention one action at a time:
it checks the pre-conditions of the current action, executes it through the action-execution
function registered for the action name, checks the post-conditions and, if the option is
complete (or the intention fails), signals the Desire Handler (satisfied / delete intention).

It runs only while the agent is focused (saliency threshold != attention threshold), in the
nested loop of Java ``Execute`` (which has no sleep).

Deviations from Java (concurrency only, behaviour is the same):
* the inner loop sleeps ``INNER_LOOP_PERIOD_MS`` (Java spins) and stops when the thread is
  stopped; the "wait for the belief update message" spins sleep too.

Java behaviour kept on purpose (README, quirks):
* The whole body is under ``if (read_and_clear(beliefs) || read_and_clear(uninhibited_data))``
  (an odd brace placement in the source). Short circuit: when ``beliefs`` is set the
  ``uninhibited_data`` flag is NOT cleared.
* A failing action prints "I delete my intention" and sets the local result to ``To_Delete`` but
  AFTER the switch, so the intention is NOT actually added to the intentions to delete.
* The satisfied/delete signals carry ALL the selected intentions, not only the evaluated one.
* ``OptionAdvancementEvaluation.evaluation_desire_satisfation`` is never reset to
  ``Not_Satisfied``: once an epistemic option completes, every later ``Correct_Executed`` is
  considered satisfied.
* ``Get_Previous_Action`` of ``Option`` returns the CURRENT action (see plan.py).
"""
from __future__ import annotations

import time  # noqa: F401  (kept: waits now go through the agent clock)
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .agent_thread import AgentBaseThread
from .desires import EpistemicDesire
from .enums import TypeIntentionEvaluated as T, TypeRelationship as R, TypeUpdateContract as C
from .handlers import ActionExecutionFunctionHandler
from .model import Belief, Predicate


def java_equals(a: Any, b: Any) -> bool:
    """``Objects.equals``: boxed values of different classes are never equal."""
    if a is None or b is None:
        return a is b
    if type(a) is not type(b):
        return False
    return a == b


_COMPARABLE = (str, int, float, bool, datetime)


class OptionAdvancementEvaluation:
    """Evaluates where an intention's option stands: pre-conditions of the current action, post-conditions of
    the previous one, desire satisfaction.
    """
    def __init__(self, owner: "ExecutiveSwitchingFunction"):
        self.parent = owner
        self.max_intentions_at_time = 1
        self.active_intentions = 0
        self.evaluation_pre_conditions_result: Optional[T] = None
        self.evaluation_post_conditions_result: Optional[T] = None
        self.evaluation_desire_satisfation = T.Not_Satisfied

    def initialize_active_intentions(self) -> None:
        self.active_intentions = 0

    def evaluate_pre_conditions(self, selected_intention: Any, uninhibited_beliefs: Dict[str, Any]) -> None:
        self.active_intentions += 1
        if self.active_intentions > self.max_intentions_at_time:
            result = T.Not_to_Execute
        else:
            result = self._check_pre_conditions(selected_intention, uninhibited_beliefs)
        self.evaluation_pre_conditions_result = result

    def _check_pre_conditions(self, selected_intention: Any, uninhibited_beliefs: Dict[str, Any]) -> T:
        """Evaluate the pre-conditions of the current action: To_Delete (no desire), Satisfied (all actions
        done), To_Execute (first action) or the result of the condition check.
        """
        desire = selected_intention.get_active_desire()
        if desire is None:
            return T.To_Delete
        options = desire.get_list_options()
        if len(options) > 0:
            option = options[selected_intention.get_selected_option_id()]
            actions_number = len(option.get_plan_actions())
            active_action_id = option.get_id_current_action()
            if active_action_id > actions_number - 1:
                return T.Satisfied
            elif active_action_id == 0:
                return T.To_Execute
            else:
                active_action = option.get_plan_actions()[active_action_id]
                truth = True
                for precondition in active_action.get_pre_conditions():
                    if precondition.get_linked_belief() is not None:
                        truth = truth and precondition.get_linked_belief().is_truth()
                    else:
                        truth = truth and self._check_condition_truth(precondition)
                return T.To_Execute if truth else T.To_Delete
        return T.To_Delete

    def _check_post_conditions(self, selected_intention: Any, uninhibited_beliefs: Dict[str, Any]) -> T:
        """Evaluate the post-conditions of the action just executed: To_Delete, Correct_Executed (nothing
        executed yet), Full_Executed (all done) or the condition check result.
        """
        desire = selected_intention.get_active_desire()
        active_option = selected_intention.get_selected_option_id()
        if desire is None or active_option < 0:
            return T.To_Delete
        option = desire.get_list_options()[active_option]
        actions_number = len(option.get_plan_actions())
        action_id_to_check = option.get_id_current_action()
        if action_id_to_check - 1 < 0:
            return T.Correct_Executed
        elif action_id_to_check >= actions_number:
            return T.Full_Executed
        active_action = option.get_plan_actions()[action_id_to_check - 1]
        truth = True
        for postcondition in active_action.get_post_conditions():
            if postcondition.get_linked_belief() is not None:
                truth = truth and postcondition.get_linked_belief().is_truth()
            else:
                truth = truth and self._check_condition_truth(postcondition)
        return T.Correct_Executed if truth else T.To_Delete

    @staticmethod
    def _check_condition_truth(condition: Predicate) -> bool:
        """Truth of one predicate against the current belief values.

        ``is``/``equal`` and ``is_not`` use Java ``equals``; the other relationships need non-null values of
        the same comparable type, otherwise an error is printed and False is returned.
        """
        subject = condition.get_subject()
        subject_value = subject.get_predicate().get_object_complement()
        complement = condition.get_object_complement()
        if isinstance(complement, Belief):
            value_to_compare = complement.get_predicate().get_object_complement()
        elif isinstance(complement, Predicate):
            value_to_compare = complement.get_object_complement()
        else:
            value_to_compare = complement
        relationship = condition.get_relationship()
        if relationship in (R.is_, R.equal):
            return java_equals(subject_value, value_to_compare)
        if relationship == R.is_not:
            return not java_equals(subject_value, value_to_compare)
        if (subject_value is None or value_to_compare is None or type(subject_value) is not type(value_to_compare)
                or not isinstance(subject_value, _COMPARABLE)):
            import sys
            print("Error: Cannot perform numeric comparisons. Objects must be non-null, of the same type, "
                  "and implement Comparable..", file=sys.stderr)
            return False
        if relationship in (R.is_in, R.is_out):
            import sys
            print("Error: The relationship '" + relationship.value + "' requires the second object to be a "
                  "Collection.", file=sys.stderr)
            return False
        if relationship == R.minor:
            return subject_value < value_to_compare
        if relationship == R.major:
            return subject_value > value_to_compare
        if relationship == R.minor_equal:
            return subject_value <= value_to_compare
        if relationship == R.major_equal:
            return subject_value >= value_to_compare
        import sys
        print("Error: Relationship type '" + str(relationship) + "' is not supported for this comparison.",
              file=sys.stderr)
        return False

    def get_evaluation_pre_conditions_result(self) -> Optional[T]:
        return self.evaluation_pre_conditions_result

    def get_evaluation_post_conditions_result(self) -> Optional[T]:
        return self.evaluation_post_conditions_result

    def get_evaluation_desire_satisfation_result(self) -> T:
        return self.evaluation_desire_satisfation

    def evaluate_post_conditions(self, selected_intention: Any, uninhibited_beliefs: Dict[str, Any]) -> None:
        if self.active_intentions > self.max_intentions_at_time:
            result = T.Not_to_Execute
        else:
            result = self._check_post_conditions(selected_intention, uninhibited_beliefs)
        self.evaluation_post_conditions_result = result

    def evaluate_desire_satisfaction(self, selected_intention: Any, uninhibited_beliefs: Dict[str, Any]) -> None:
        if selected_intention.get_selected_option().actions_completed():
            if isinstance(selected_intention.get_attentional_desire(), EpistemicDesire):
                self.evaluation_desire_satisfation = T.Satisfied


class OptionExecution:
    """Executes the current action of the selected option through the action-execution function and advances
    the option when it succeeded.
    """
    def __init__(self, owner: "ExecutiveSwitchingFunction"):
        self.parent = owner
        self.plan_executive_function_handler = ActionExecutionFunctionHandler()   # unused in Java too
        self.action_execution: Any = None
        self.global_workspace: Any = None

    def execute(self, selected_intention: Any, beliefs: Dict[str, Any]) -> Any:
        """Run the current action; on success advance the option's current action, otherwise print the error
        message; returns the result with the action attached.
        """
        desire = selected_intention.get_active_desire()
        option = desire.get_list_options()[selected_intention.get_selected_option_id()]
        action = option.get_plan_actions()[option.get_id_current_action()]
        result = self.action_execution.execute(action, beliefs)
        result.action = action
        if result.get_result():
            option.next_id_current_action()
        else:
            print("An error was encountered while executing the Action Function Name: "
                  + str(action.get_action_name()))
        return result

    def set_data(self, agent: Any) -> None:
        self.global_workspace = agent.get_global_workspace()
        self.action_execution = agent.get_action_control().get_action_execution()

    def get_global_workspace(self) -> Any:
        return self.global_workspace

    def register_plan_execution_funtion_to_execute(self, action_name: str, func: Callable) -> None:
        self.plan_executive_function_handler.register_function(action_name, func)

    def unregister_plan_execution_function_to_execute(self, action_name: str) -> bool:
        return self.plan_executive_function_handler.unregister_function(action_name)


class ExecutiveSwitchingFunction(AgentBaseThread):
    """Executive Switching thread: executes the plan of the first selected intention step by step while the
    agent is focused (see the module docstring).
    """
    INNER_LOOP_PERIOD_MS = 5

    def __init__(self, agent: Any):
        super().__init__(agent, "Executive Switching Function")
        self.global_workspace = agent.get_global_workspace()
        self.option_advancement_evaluation = OptionAdvancementEvaluation(self)
        self.option_execution = OptionExecution(self)
        self.option_execution.set_data(self.agent)
        self.selected_intentions: List[Any] = []
        self.map_uninhibited_beliefs: Dict[str, Any] = {}
        self.satisfied_attentional_desires: List[Any] = []
        self.intentions_to_delete: List[Any] = []

    def insert_in_list_update_contract(self) -> None:
        gw = self.agent.get_global_workspace()
        for contract in (C.Internal_Signals, C.Updated_Selected_Intentions, C.Internal_Signals_Abort_Option,
                         C.Updated_Thresholds, C.Updated_Uninhibited_Data, C.Updated_Beliefs,
                         C.Updated_Executed_Action):
            gw.insert_for_update_contract(contract, self)

    # ------------------------------------------------------------------ helpers
    def _beliefs_update_pending(self) -> bool:
        mh = self.message_handler
        return mh.read_value("beliefs") or mh.read_value("uninhibited_data")

    def _wait_for_beliefs_update(self) -> None:
        while not self._beliefs_update_pending():
            if not self.read_continue_thread():
                return
            self.wait_a_time(self.INNER_LOOP_PERIOD_MS)

    # ------------------------------------------------------------------ loop body
    def execute(self) -> None:
        """Nested loop that runs while the agent is focused (thresholds differ): refresh intentions and
        beliefs, then run one switching step every ``INNER_LOOP_PERIOD_MS``.
        """
        gw = self.global_workspace
        mh = self.message_handler
        thresholds = gw.get_saliency_and_attention_thresholds()
        while thresholds.get_object_first() != thresholds.get_object_second():
            if not self.read_continue_thread():
                return
            thresholds = gw.get_saliency_and_attention_thresholds()
            intentions_to_abort: Dict[Any, None] = {}
            self.is_in_pause()
            if mh.read_value_and_clear("selected_intentions"):
                self.selected_intentions = list(gw.get_selected_intentions())
            if mh.read_value_and_clear("beliefs") or mh.read_value_and_clear("uninhibited_data"):
                self.map_uninhibited_beliefs = dict(gw.map_uninhibited_beliefs)
                for message in mh.read_and_clear_internal_signals_abort_option_messages():
                    for obj in message.read_data_and_clean():
                        intentions_to_abort[obj] = None
                self._step(intentions_to_abort)
            self.wait_a_time(self.INNER_LOOP_PERIOD_MS)

    def _step(self, intentions_to_abort: Dict[Any, None]) -> None:
        """One switching step for the first selected intention: evaluate, execute the action, evaluate again
        and signal satisfied/delete intentions to the Desire Handler.
        """
        gw = self.global_workspace
        mh = self.message_handler
        evaluation = self.option_advancement_evaluation
        execute_action: Optional[T] = None
        self.satisfied_attentional_desires = []
        self.intentions_to_delete = []
        evaluation.initialize_active_intentions()
        if len(self.selected_intentions) == 0:
            return
        selected_intention = self.selected_intentions[0]
        desire2 = selected_intention.get_active_desire()
        if desire2 is None or len(desire2.get_list_options()) == 0:
            return
        if selected_intention not in intentions_to_abort:
            desire = selected_intention.get_active_desire()
            if desire is not None:
                if len(desire.get_list_options()) > 0:
                    option = desire.get_list_options()[selected_intention.get_selected_option_id()]
                    if len(option.get_plan_actions()) > 0:
                        evaluation.evaluate_pre_conditions(selected_intention, self.map_uninhibited_beliefs)
                        execute_action = evaluation.get_evaluation_pre_conditions_result()
                    else:
                        execute_action = T.Not_to_Execute
                else:
                    execute_action = T.Not_to_Execute
            else:
                execute_action = T.To_Delete
        else:
            execute_action = T.To_Delete

        result = None
        if execute_action == T.To_Execute:
            result = self.option_execution.execute(selected_intention, self.map_uninhibited_beliefs)
            if len(result.get_beliefs_to_change()) > 0:
                gw.update_uninhibited_conscious_beliefs(dict(result.get_beliefs_to_change()))
            if len(result.get_beliefs_to_monitor()) > 0:
                beliefs_to_wait = dict(result.get_beliefs_to_monitor())
                while len(beliefs_to_wait) > 0:
                    self._wait_for_beliefs_update()
                    if not self.read_continue_thread():
                        return
                    for belief_name in list(result.get_beliefs_to_monitor()):
                        current = self.map_uninhibited_beliefs[belief_name].get_predicate().get_object_complement()
                        if not java_equals(beliefs_to_wait.get(belief_name), current):
                            beliefs_to_wait.pop(belief_name, None)
                    self.wait_a_time(self.INNER_LOOP_PERIOD_MS)
            if len(result.get_practical_desires()) > 0:
                gw.add_inhibited_practical_attentional_desires(list(result.get_practical_desires()))
            if len(result.get_stimuli()) > 0:
                gw.set_stimuli(list(result.get_stimuli()))
            if not result.get_result():
                print("Result false! Error while executing an action!\nI delete my intention")
                execute_action = T.To_Delete        # after the switch in Java: has no further effect
        elif execute_action == T.Satisfied:
            self.satisfied_attentional_desires.append(selected_intention.get_active_desire())
        elif execute_action == T.To_Delete:
            self.intentions_to_delete.append(selected_intention)
        elif execute_action == T.Not_to_Execute:
            pass
        elif execute_action is None:
            raise AttributeError("switch on null evaluation result")      # Java NullPointerException

        if execute_action == T.To_Execute:
            if len(result.get_beliefs_to_change()) > 0:
                self._wait_for_beliefs_update()
            temp_beliefs = dict(gw.get_map_uninhibited_beliefs())
            evaluation.evaluate_post_conditions(selected_intention, temp_beliefs)
            execute_action = evaluation.get_evaluation_post_conditions_result()
            if execute_action == T.Full_Executed:
                self.satisfied_attentional_desires.append(selected_intention.get_active_desire())
            if execute_action == T.Correct_Executed:
                evaluation.evaluate_desire_satisfaction(selected_intention, temp_beliefs)
                if evaluation.get_evaluation_desire_satisfation_result() == T.Satisfied:
                    self.satisfied_attentional_desires.append(selected_intention.get_active_desire())

        if len(self.satisfied_attentional_desires) > 0:
            gw.broadcast_internal_signals_messages(C.Internal_Signals_Satisfied_Intention, self.name,
                                                   list(self.selected_intentions))
        if len(self.intentions_to_delete) > 0:
            gw.broadcast_internal_signals_messages(C.Internal_Signals_Delete_Intention, self.name,
                                                   list(self.selected_intentions))

    def register_plan_execution_funtion_to_execute(self, action_name: str, func: Callable) -> None:
        self.option_execution.register_plan_execution_funtion_to_execute(action_name, func)

    def unregister_plan_execution_function_to_execute(self, action_name: str) -> bool:
        return self.option_execution.unregister_plan_execution_function_to_execute(action_name)
