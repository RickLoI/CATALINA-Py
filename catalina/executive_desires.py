"""Desire Handler executive.

Java: TDesire_Handler, TIntention_Deletion, TDemotion_Desires, TExogenous_Desire_Promotion,
TEndogenous_Desire_Promotion.

One loop does, in this order: delete errata / satisfied intentions, demote active desires whose
saliency fell below the saliency threshold, promote exogenous desires (from stimuli: epistemic
ones through the stimulus->epistemic-desire functions, practical ones through the exogenous
functions) and endogenous desires (standing practical desires whose trigger condition holds and
whose saliency reaches the threshold), and finally mark the promoted ones as active in the Global
Workspace.

Java behaviour kept on purpose:
* ``DemotionDesires.execute`` examines ALL the uninhibited desires (not only the active ones) and
  uses only the saliency threshold.
* Intention deletion broadcasts the whole data of the internal-signal message (the executives
  that signal send ``selected_intentions``, i.e. all of them, not only the failed one).
* ``execute`` of ``ExogenousDesirePromotion`` always returns False (unused).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .agent_thread import AgentBaseThread
from .desires import EpistemicDesire, PracticalDesire
from .enums import TypeStatusDesire, TypeUpdateContract as C
from .formula import BooleanExpressionEvaluator
from .handlers import ExogenousAttentionalDesiresFunctionHandler
from .maps import MapExogenousFunctionsHandler


class IntentionDeletion:
    """Handles the internal signals that delete or satisfy intentions (Java: TIntention_Deletion)."""
    def __init__(self, owner: "DesireHandler"):
        self.parent = owner
        self.global_workspace = owner.get_global_workspace()

    def execute(self) -> None:
        self.remove_errata_intentions()
        self.remove_satisfied_intentions()

    def remove_errata_intentions(self) -> None:
        """For each 'delete intention' signal: detach the intention from its desire, clear the options, remove
        the intentions from the Global Workspace and put the desires back to Standing.
        """
        signals = list(self.parent.message_handler.read_and_clear_internal_signals_delete_intention_messages())
        if len(signals) > 0:
            to_handle: Dict[Any, None] = {}
            for message in signals:
                for intention in message.read_data():
                    to_handle[intention] = None
            desires: List[Any] = []
            for intention in to_handle:
                desire = intention.get_active_desire()
                if desire is not None:
                    desire.set_related_intention(None)
                    desire.clear_options()
                    desires.append(desire)
                intention.set_desire(None)
            self.global_workspace.remove_intentions(list(to_handle))
            self.global_workspace.mark_as_standing_desires(desires)
            self.global_workspace.broadcast_signal(C.Updated_Selected_Intentions)

    def remove_satisfied_intentions(self) -> None:
        """For each 'satisfied intention' signal: store its plan in the plan library and mark its desire as
        Satisfied.
        """
        satisfied: List[Any] = []
        signals = list(self.parent.message_handler.read_and_clear_internal_signals_satisfied_intention_messages())
        if len(signals) > 0:
            to_handle: Dict[Any, None] = {}
            for message in signals:
                for intention in message.read_data():
                    to_handle[intention] = None
            for intention in to_handle:
                self.global_workspace.insert_plan_in_plan_library(intention)
                desire = intention.get_active_desire()
                if desire is not None:
                    satisfied.append(desire)
            self.global_workspace.mark_as_satisfied_desires(satisfied)


class DemotionDesires:
    """Sends back to Standing the uninhibited desires whose saliency is below the saliency threshold (see the
    module docstring for the Java quirk).
    """
    def __init__(self, owner: "DesireHandler"):
        self.parent = owner
        self.global_workspace = owner.get_global_workspace()

    def execute(self) -> None:
        if self.parent.get_updated_uninhibited_data():
            gw = self.global_workspace
            active_desires = [d for d in gw.get_unhinibited_desires() if not isinstance(d, EpistemicDesire)]
            saliency_threshold = self.parent.get_saliency_threshold()
            to_standing = [d for d in active_desires if d.get_saliency() < saliency_threshold]
            if len(to_standing) > 0:
                gw.mark_as_standing_desires(to_standing)


class ExogenousDesirePromotion:
    """Turns new stimuli into exogenous (epistemic and practical) desires through the registered functions.
    """
    def __init__(self, owner: "DesireHandler"):
        self.owner = owner
        self.global_workspace = owner.get_global_workspace()
        self.map_stimulus_to_epistemic_desires = MapExogenousFunctionsHandler()
        self.exogenous_attentional_desires_function_handler = ExogenousAttentionalDesiresFunctionHandler()
        self.exogenous_attentional_desires_function_handler.set_recall_belief(self.global_workspace.recal_beliefs)
        self.exogenous_epistemic_desire: Dict[Any, None] = {}
        self.exogenous_practical_desire: Dict[Any, None] = {}
        self.computed_new_exogenous_desire = False

    def execute(self) -> bool:
        """If new stimuli arrived: run the exogenous-promotion function of each stimulus type and collect the
        epistemic desires and practical-desire data it raises (which may also add stimuli).
        """
        update_stimuli = self.owner.message_handler.read_value_and_clear("stimuli")
        self.exogenous_epistemic_desire.clear()
        self.exogenous_practical_desire.clear()
        if update_stimuli:
            gw = self.global_workspace
            map_beliefs: Dict[str, Any] = {}
            map_beliefs.update(gw.get_map_uninhibited_beliefs())
            stimuli: Dict[Any, None] = {}
            epistemic: List[Any] = []
            practical_data: List[Any] = []
            stimuli.update(dict.fromkeys(gw.get_stimuli()))
            new_stimuli = list(stimuli)
            for stimulus in new_stimuli:
                raised = self.exogenous_attentional_desires_function_handler.execute_function_for_desire_to_raise(
                    stimulus, map_beliefs)
                stimuli.update(dict.fromkeys(raised.get_stimuli()))
                practical_data.extend(raised.get_practical_desires_data())
            if len(practical_data) > 0:
                gw.add_inhibited_practical_attentional_desires(practical_data)
            for stimulus in list(stimuli):
                desire = self.map_stimulus_to_epistemic_desires.execute_epistemic_function(gw, stimulus)
                if desire is not None:
                    epistemic.append(desire)
            self.exogenous_epistemic_desire.update(dict.fromkeys(epistemic))
        return False

    def register_epistemic_function(self, stimulus_type: str, func: Callable) -> None:
        self.map_stimulus_to_epistemic_desires.register_epistemic_function(stimulus_type, func)

    def unregister_epistemic_function(self, stimulus_type: str) -> None:
        self.map_stimulus_to_epistemic_desires.unregister_epistemic_function(stimulus_type)

    def register_practical_function(self, stimulus_type: str, func: Callable) -> None:
        self.exogenous_attentional_desires_function_handler.register_function(stimulus_type, func)

    def unregister_practical_function(self, stimulus_type: str) -> None:
        self.exogenous_attentional_desires_function_handler.unregister_function(stimulus_type)

    def has_new_exogenous_desire(self) -> bool:
        return self.computed_new_exogenous_desire

    def get_exogenous_epistemic_desire(self) -> List[Any]:
        result = list(self.exogenous_epistemic_desire)
        self.exogenous_epistemic_desire.clear()
        return result

    def get_exogenous_practical_desire(self) -> List[Any]:
        result = list(self.exogenous_practical_desire)
        self.exogenous_practical_desire.clear()
        return result


class EndogenousDesirePromotion:
    """Promotes standing practical desires whose trigger condition holds and whose saliency passes the
    thresholds.
    """
    def __init__(self, owner: "DesireHandler"):
        self.parent = owner
        self.global_workspace = owner.get_global_workspace()
        self.expression_evaluator = BooleanExpressionEvaluator()
        self.pre_conditions: List[Any] = []
        self.selected_intentions: List[Any] = []
        self.inhibited_endogenous_desires: Dict[Any, None] = {}
        self.uninhibited_endogenous_desires: Dict[Any, None] = {}
        self.computed_new_exogenous_desire = False
        self.compute_unhinibited_regions_for_desire: Callable = None
        self.executed = False

    def execute(self) -> None:
        """If standing desires, beliefs, uninhibited data or preconditions changed: evaluate the trigger
        conditions of all practical desires and split them into inhibited/uninhibited endogenous desires
        using the thresholds.
        """
        self.executed = False
        mh = self.parent.message_handler
        updated_standing = mh.read_value_and_clear("standing_desires")
        updated_beliefs = mh.read_value_and_clear("beliefs")
        updated_preconditions = mh.read_value_and_clear("preconditions")
        updated_data = self.parent.get_updated_uninhibited_data()
        if updated_standing or updated_beliefs or updated_data or updated_preconditions:
            self.inhibited_endogenous_desires.clear()
            self.uninhibited_endogenous_desires.clear()
            gw = self.global_workspace
            saliency_threshold = self.parent.get_saliency_threshold()
            attention_threshold = self.parent.get_attention_threshold()
            if updated_data or updated_preconditions:
                self.pre_conditions = gw.get_preconditions()
                self.update_expression_evaluator(self.pre_conditions)
            practical = gw.get_all_practical_desires()
            inhibited_practical = gw.get_inhibited_practical_desires_from_lt()
            uninhibited_practical = [d for d in practical if d not in inhibited_practical]
            to_promote: List[Any] = []
            for desire in uninhibited_practical:
                if desire.get_status_desire() == TypeStatusDesire.Standing:
                    if self.verify_precondition(desire):
                        if desire.get_saliency() >= saliency_threshold:
                            to_promote.append(desire)
            inhibited_to_promote: List[Any] = []
            for desire in inhibited_practical:
                if desire.get_status_desire() == TypeStatusDesire.Standing:
                    if self.verify_precondition(desire):
                        if desire.get_saliency() >= attention_threshold:
                            inhibited_to_promote.append(desire)
            self.uninhibited_endogenous_desires.update(dict.fromkeys(to_promote))
            self.inhibited_endogenous_desires.update(dict.fromkeys(inhibited_to_promote))
            self.computed_new_exogenous_desire = (len(self.uninhibited_endogenous_desires) > 0 or
                                                  len(self.inhibited_endogenous_desires) > 0)

    def update_expression_evaluator(self, pre_conditions: List[Any]) -> None:
        self.expression_evaluator.clear()
        for belief in pre_conditions:
            self.expression_evaluator.set_variable(belief.get_name(), belief.is_truth())

    def verify_precondition(self, practical_desire: Any) -> bool:
        """True if the desire has no trigger condition or its boolean formula is true given the current truth
        value of its beliefs.
        """
        result = True
        formula = practical_desire.get_trigger_condition_formula()
        if practical_desire is not None:
            if formula != "":
                self.expression_evaluator.clear()
                for belief in practical_desire.get_trigger_condition().get_beliefs():
                    self.expression_evaluator.set_variable(belief.get_name(), belief.is_truth())
                result = self.expression_evaluator.evaluate(formula)
        return result

    def set_compute_unhinibited_regions_for_desire_function(self, func: Callable) -> None:
        self.compute_unhinibited_regions_for_desire = func

    def has_new_exogenous_desire(self) -> bool:
        return self.computed_new_exogenous_desire

    def get_uninhibited_endogenous_desires(self) -> List[Any]:
        result = list(self.uninhibited_endogenous_desires)
        self.uninhibited_endogenous_desires.clear()
        return result

    def get_inhibited_endogenous_desires(self) -> List[Any]:
        result = list(self.inhibited_endogenous_desires)
        self.inhibited_endogenous_desires.clear()
        return result


class DesireHandler(AgentBaseThread):
    """Executive Desire Handler thread: one loop = delete intentions, demote, promote exogenous and endogenous
    desires, mark the promoted ones as active.
    """
    def __init__(self, agent: Any):
        super().__init__(agent, "Executive Desire Handler Function")
        self.global_workspace = self.agent.get_global_workspace()
        self.exogenous_desire_promotion = ExogenousDesirePromotion(self)
        self.endogenous_desire_promotion = EndogenousDesirePromotion(self)
        self.intention_deletion = IntentionDeletion(self)
        self.demotion_desires = DemotionDesires(self)
        self.saliency_threshold = 0.0
        self.attention_threshold = 0.0
        self.updated_uninhibited_data = False

    def insert_in_list_update_contract(self) -> None:
        gw = self.agent.get_global_workspace()
        for contract in (C.Internal_Signals_Delete_Intention, C.Internal_Signals_Satisfied_Intention,
                         C.Updated_Uninhibited_Data, C.Updated_Thresholds, C.Updated_Standing_Desires,
                         C.Updated_Beliefs, C.Updated_Preconditions, C.Updated_Stimuli):
            gw.insert_for_update_contract(contract, self)

    def execute(self) -> None:
        """One loop: refresh thresholds, run the four sub-steps in order and mark the promoted desires as
        Active in the Global Workspace.
        """
        mh = self.message_handler
        updated_thresholds = mh.read_value_and_clear("thresholds")
        self.updated_uninhibited_data = mh.read_value_and_clear("uninhibited_data")
        if updated_thresholds:
            thresholds = self.global_workspace.get_saliency_and_attention_thresholds()
            self.saliency_threshold = thresholds.get_object_first()
            self.attention_threshold = thresholds.get_object_second()
        self.intention_deletion.execute()
        self.demotion_desires.execute()
        self.exogenous_desire_promotion.execute()
        self.endogenous_desire_promotion.execute()
        inhibited: List[Any] = []
        inhibited.extend(self.exogenous_desire_promotion.get_exogenous_epistemic_desire())
        uninhibited = list(self.endogenous_desire_promotion.get_uninhibited_endogenous_desires())
        inhibited.extend(self.endogenous_desire_promotion.get_inhibited_endogenous_desires())
        self.global_workspace.mark_as_active_desires(uninhibited, inhibited)

    def get_global_workspace(self) -> Any:
        return self.global_workspace

    def register_epistemic_function(self, stimulus_type: str, func: Callable) -> None:
        self.exogenous_desire_promotion.register_epistemic_function(stimulus_type, func)

    def register_practical_function(self, stimulus_type: str, func: Callable) -> None:
        self.exogenous_desire_promotion.register_practical_function(stimulus_type, func)

    def unregister_epistemic_function(self, stimulus_type: str) -> None:
        self.exogenous_desire_promotion.unregister_epistemic_function(stimulus_type)

    def unregister_practical_function(self, stimulus_type: str) -> None:
        self.exogenous_desire_promotion.unregister_practical_function(stimulus_type)

    def get_saliency_threshold(self) -> float:
        return self.saliency_threshold

    def get_attention_threshold(self) -> float:
        return self.attention_threshold

    def get_updated_uninhibited_data(self) -> bool:
        return self.updated_uninhibited_data
