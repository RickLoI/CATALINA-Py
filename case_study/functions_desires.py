"""Exogenous desire promotion of the case study (Java: TFunctions_for_Exogenous_Desire_Promotion).

* ``BLTS_Stimulus_Danger_on_the_Route`` -> epistemic desire ``Inquiry_Estimated_Delay``.
* ``BLTS_Stimulus_Low_Fuel``            -> practical desire ``Refuel`` (with its means-end function and
  its belief/region inhibition functions).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from catalina.desire_data import PracticalDesireData
from catalina.desires import EpistemicDesire, PracticalDesire
from catalina.enums import TypeTemporalOperator
from catalina.formula import PropositionalFormula, TemporalOperator, TemporalPropositionalFormula
from catalina.handlers import ExogenousPromotionResult


class FunctionsForExogenousDesirePromotion:
    """Exogenous desire promotion: what the Desire Handler raises when a stimulus arrives (danger on the route
    -> epistemic desire; low fuel -> practical desire).
    """
    def __init__(self, demo: Any):
        self.demo = demo
        self.common_functions = demo.common_functions
        self.belief_inhibition_functions = demo.functions_for_belief_inhibition_function

    def add_functions_to_exogenous_desire_promotion(self, desire_handler) -> None:
        desire_handler.register_epistemic_function("BLTS_Stimulus_Danger_on_the_Route",
                                                   self.epistemic_desire_from_blts_stimulus_danger_on_the_route)
        desire_handler.register_practical_function("BLTS_Stimulus_Low_Fuel",
                                                   self.practical_desire_from_blts_stimulus_low_fuel)

    def practical_desire_from_blts_stimulus_low_fuel(self, stimulus, beliefs, recall_belief
                                                     ) -> ExogenousPromotionResult:
        """Low-fuel stimulus -> practical desire to refuel (reward 0.4, finally interval of 10 hours from the
        current time).
        """
        result = ExogenousPromotionResult()
        bl_refuel_to_city = beliefs.get("BL_Refuel_to_City")
        saliency = stimulus.get_saliency()
        reward = 0.4
        relax_preference = 0.4
        bl_current_time = beliefs.get("BL_Current_Time")
        finally_start = bl_current_time.get_predicate().get_object_complement()
        finally_end = finally_start + timedelta(hours=10)
        temporal_operator = TemporalOperator()
        temporal_operator.set_type_temporal_operator(TypeTemporalOperator.Finally)
        temporal_operator.set_start_time(finally_start)
        temporal_operator.set_end_time(finally_end)
        formula = TemporalPropositionalFormula()
        formula.set_temporal_operator(temporal_operator)
        formula.set_beliefs([bl_refuel_to_city])
        formula.set_formula(bl_refuel_to_city.get_name())
        formula.set_list_temporal_propositional_formula_names(None)
        # precondition of the desire = the belief in its trigger condition
        bl_low_fuel_level = beliefs.get("BL_Low_Fuel_Level")
        trigger_condition = PropositionalFormula()
        trigger_condition.set_beliefs([bl_low_fuel_level])
        trigger_condition.set_formula(bl_low_fuel_level.get_name())
        refuel = PracticalDesire("Refuel", formula, trigger_condition, saliency, reward, relax_preference,
                                 [], [], finally_start, finally_end, None, None, None, None, None, None)
        inh = self.demo.functions_for_belief_inhibition_function
        refuel.set_beliefs_name_for_reasoner(list(inh.get_desires_beliefs_functions().reasoner_beliefs_for_refuel(refuel)))
        refuel.set_regions_name_for_reasoner(
            list(inh.get_desires_regions_functions().reasoner_get_regions_for_refuel(beliefs)))
        data = PracticalDesireData()
        data.set_practical_desire(refuel)
        data.set_means_end_reasoner_function(self.demo.means_end_reasoner_function.reasoner_function_for_refuel)
        data.add_beliefs_inhibition_functions(
            self.belief_inhibition_functions.get_desires_beliefs_functions().inhibition_beliefs_for_refuel)
        data.add_regions_inhibition_functions(
            self.belief_inhibition_functions.get_desires_regions_functions().inhibition_regions_for_refuel)
        result.add_practical_desires_data([data])
        result.set_result(True)
        return result

    def epistemic_desire_from_blts_stimulus_danger_on_the_route(self, global_workspace, stimulus
                                                                ) -> EpistemicDesire:
        """Danger stimulus -> epistemic desire 'Inquiry_Estimated_Delay' (reward 0.3), with the beliefs the
        reasoner needs.
        """
        saliency = stimulus.get_saliency()
        reward = 0.3
        relax_preference = 0.3
        trigger_condition = PropositionalFormula()
        green = list(global_workspace.get_green_desires_by_names_from_mm([]))
        quality = list(global_workspace.get_quality_desires_by_names_from_mm([]))
        epistemic = EpistemicDesire("Inquiry_Estimated_Delay", stimulus, trigger_condition, saliency, reward,
                                    relax_preference, green, quality, None, None)
        names = self.demo.functions_for_belief_inhibition_function.get_desires_beliefs_functions(
        ).reasoner_beliefs_for_stimulus_danger_on_the_route(epistemic)
        epistemic.set_beliefs_name_for_reasoner(list(names))
        return epistemic
