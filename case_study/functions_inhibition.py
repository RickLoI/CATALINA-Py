"""Inhibition side of the case study.

Java: TDesires_Beliefs_Functions, TDesires_Regions_Functions, TDesires_Precondictions_Functions,
TDesires_Executive_Funtions, TFunctions_for_Inhibition_Function (with the two Global Workspace
callbacks), TFunctions_for_Region_Inhibition_Function.

Sets of names are returned as insertion-ordered dicts (``name -> None``), standing for the Java
``HashSet<String>``; consumers only test membership.

Java behaviour kept on purpose:
* ``GlobalWorkspace_CallBack`` reads the *first* object of the thresholds twice, so the agent
  status it reports is always ``Unfocused``.
* ``Reasoner_Beliefs_For_Refuel`` uses the *Come Back* list (not the Refuel list).
* ``TDesires_Precondictions_Functions.Get_Destination_City_Preconditions`` would throw an NPE if
  the desire had no cached list; it is not used by the case study and is ported as is.

The Swing "Global Workspace" window texts become ``gw_update`` / ``gw_signal`` events.
"""
from __future__ import annotations

from typing import Any, Dict, List

from catalina.model import Belief


def _names(items) -> Dict[str, None]:
    return {n: None for n in items}


class DesiresBeliefsFunctions:
    """Java: TDesires_Beliefs_Functions."""

    def __init__(self) -> None:
        self.list_for_reasoner_come_back: Dict[str, None] = {}
        self.list_for_reasoner_destination_city: Dict[str, None] = {}
        self.list_for_reasoner_stimulus_danger_on_the_route: Dict[str, None] = {}
        self.list_for_reasoner_stimulus_danger_data_from_tcs: Dict[str, None] = {}
        self.list_for_reasoner_refuel: Dict[str, None] = {}
        self._initialize_list_for_destination_city()
        self._initialize_list_for_come_back()
        self._initialize_list_for_stimulus_danger_on_the_route()
        self._initialize_list_for_refuel()

    # ---- static lists (same content and order as the Java source)
    def _initialize_list_for_come_back(self) -> None:
        """Names of the beliefs the reasoner needs for the come-back desire."""
        self.list_for_reasoner_come_back = _names([
            "BL_Closed_Routes", "BL_Temporary_Closed_Routes", "BL_Dangerous_Position_Route", "BL_Map",
            "BL_Come_Back_to_City", "BL_Current_Time", "BLT_Destination_City", "BL_Danger_on_the_Route",
            "BL_Next_Position_City", "BL_Next_Position_Route", "BL_Next_Position_Step",
            "BL_Position_City", "BL_Position_Route", "BL_Position_Step",
            "BL_Previous_Position_City", "BL_Previous_Position_Route", "BL_Previous_Position_Step",
            "BL_Routes_performed_for_each_Practical_Desires", "BL_Temporary_Closed_Routes",
            "ST_Stimulus_Danger_on_the_Route", "ST_Stimulus_Irrelevant", "ST_Stimulus_Ok_Correct_Movement",
            "ST_Stimulus_Route_Status", "ST_Stimulus_Temporary_Closed_Route", "BL_Fuel_Level",
            "ST_Stimulus_Low_Fuel", "BL_Low_Fuel_Level_Warning", "BL_Refuel_to_City", "BL_Low_Fuel_Level"])

    def _initialize_list_for_refuel(self) -> None:
        """Names of the beliefs the reasoner needs for the refuel desire."""
        self.list_for_reasoner_refuel = _names([
            "BL_Closed_Routes", "BL_Temporary_Closed_Routes", "BL_Dangerous_Position_Route", "BL_Map",
            "BL_Current_Time", "BL_Danger_on_the_Route", "BL_Next_Position_City", "BL_Next_Position_Route",
            "BL_Next_Position_Step", "BL_Position_City", "BL_Position_Route", "BL_Position_Step",
            "BL_Previous_Position_City", "BL_Previous_Position_Route", "BL_Previous_Position_Step",
            "BL_Routes_performed_for_each_Practical_Desires", "BL_Temporary_Closed_Routes",
            "ST_Stimulus_Danger_on_the_Route", "ST_Stimulus_Irrelevant", "ST_Stimulus_Ok_Correct_Movement",
            "ST_Stimulus_Route_Status", "ST_Stimulus_Temporary_Closed_Route", "BL_Fuel_Level",
            "ST_Stimulus_Low_Fuel", "BL_Low_Fuel_Level_Warning", "BLT_City_to_Refuel", "BL_Refuel_to_City",
            "BL_Low_Fuel_Level"])

    def _initialize_list_for_destination_city(self) -> None:
        """Names of the beliefs the reasoner needs for the 'visit a city' desires."""
        self.list_for_reasoner_destination_city = _names([
            "BL_Closed_Routes", "BL_Temporary_Closed_Routes", "BL_Dangerous_Position_Route", "BL_Map",
            "BL_Come_Back_to_City", "BLT_Destination_City", "BL_Current_Time", "BL_Danger_on_the_Route",
            "BL_Next_Position_City", "BL_Next_Position_Route", "BL_Next_Position_Step",
            "BL_Position_City", "BL_Position_Route", "BL_Position_Step",
            "BL_Previous_Position_City", "BL_Previous_Position_Route", "BL_Previous_Position_Step",
            "BL_Routes_performed_for_each_Practical_Desires", "BL_Temporary_Closed_Routes",
            "ST_Stimulus_Danger_on_the_Route", "ST_Stimulus_Irrelevant", "ST_Stimulus_Ok_Correct_Movement",
            "ST_Stimulus_Route_Status", "ST_Stimulus_Temporary_Closed_Route", "BL_Fuel_Level",
            "ST_Stimulus_Low_Fuel", "BL_Low_Fuel_Level_Warning", "BL_Refuel_to_City",
            "BL_Current_Travel_Intention_Satisfaction_Time", "BL_Previous_Travel_Intention_Satisfaction_Time",
            "BL_Previous_Travel_Intention_Max_Satisfaction_Time", "BL_Temporary_Closed_Duration",
            "BL_Low_Fuel_Level"])

    def _initialize_list_for_stimulus_danger_on_the_route(self) -> None:
        """Names of the beliefs the epistemic desire about a danger on the route needs."""
        self.list_for_reasoner_stimulus_danger_on_the_route = _names([
            "BL_Danger_on_the_Route", "BL_Dangerous_Position_Route", "BL_Come_Back_to_City",
            "BLT_Destination_City", "BL_Current_Time", "BL_Map", "BL_Temporary_Closed_Routes",
            "BL_Position_City", "BL_Position_Route", "BL_Position_Step", "BL_Next_Position_City",
            "BL_Next_Position_Route", "BL_Next_Position_Step", "ST_Stimulus_Danger_on_the_Route",
            "ST_Stimulus_Irrelevant", "ST_Stimulus_Ok_Correct_Movement", "ST_Stimulus_Route_Status",
            "ST_Stimulus_Temporary_Closed_Route", "ST_Stimulus_Danger_Data_from_TCS", "BL_Fuel_Level",
            "ST_Stimulus_Low_Fuel", "BL_Low_Fuel_Level_Warning", "BL_Refuel_to_City", "BL_Low_Fuel_Level",
            "BL_Current_Travel_Intention_Satisfaction_Time", "BL_Previous_Travel_Intention_Satisfaction_Time",
            "BL_Previous_Travel_Intention_Max_Satisfaction_Time", "BL_Temporary_Closed_Duration"])

    # ---- belief inhibition functions (desire, map of beliefs) -> names
    def inhibition_beliefs_for_destination_city(self, attentional_desire, map_beliefs) -> Dict[str, None]:
        """Beliefs kept conscious for a 'visit a city' desire: the fixed list plus the status of every route of the selected option and of its specular route.
        """
        result = dict(self.list_for_reasoner_destination_city)
        if attentional_desire is not None:
            intention = attentional_desire.get_related_intention()
            if intention is not None:
                selected_option_id = intention.get_selected_option_id()
                if selected_option_id >= 0:
                    option_simulation = attentional_desire.get_list_options()[selected_option_id]
                    env = map_beliefs.get("BL_Map").get_predicate().get_object_complement()
                    for route in option_simulation.path.routes:
                        specular = env.get_specular_route(route)
                        result["BL_Route_Status_" + str(route)] = None
                        result["BL_Route_Status_" + str(specular)] = None
                    for city in option_simulation.path.destinations:
                        result["BL_City_Visited_" + str(city)] = None
                    result.update(self._get_beliefs_by_selected_option(option_simulation))
        return result

    def inhibition_beliefs_for_come_back(self, attentional_desire, map_beliefs) -> Dict[str, None]:
        """Beliefs kept conscious for the come-back desire: the fixed list plus the status of the dangerous route and of its specular route.
        """
        result = dict(self.list_for_reasoner_come_back)
        env = map_beliefs.get("BL_Map").get_predicate().get_object_complement()
        bl_dangerous_route = map_beliefs.get("BL_Dangerous_Position_Route")
        dangerous_route_value = bl_dangerous_route.get_predicate().get_object_complement()
        specular = env.get_specular_route(dangerous_route_value)
        result["BL_Route_Status_" + str(dangerous_route_value)] = None
        result["BL_Route_Status_" + str(specular)] = None
        result[bl_dangerous_route.get_name()] = None
        return result

    def inhibition_beliefs_for_refuel(self, attentional_desire, map_beliefs) -> Dict[str, None]:
        """Beliefs kept conscious for the refuel desire: the fixed list plus the status of the current (or next) route and of its specular route.
        """
        result = dict(self.list_for_reasoner_refuel)
        env = map_beliefs.get("BL_Map").get_predicate().get_object_complement()
        route_position = map_beliefs.get("BL_Position_Route").get_predicate().get_object_complement()
        if route_position == -1:
            route_position = map_beliefs.get("BL_Next_Position_Route").get_predicate().get_object_complement()
        specular = env.get_specular_route(route_position)
        result["BL_Route_Status_" + str(route_position)] = None
        result["BL_Route_Status_" + str(specular)] = None
        return result

    def inhibition_beliefs_for_stimulus_danger_on_the_route(self, attentional_desire, map_beliefs
                                                            ) -> Dict[str, None]:
        """Beliefs kept conscious for the danger epistemic desire: the fixed list plus the status of the route where the danger was seen.
        """
        result = dict(self.list_for_reasoner_stimulus_danger_on_the_route)
        belief = map_beliefs.get("ST_Stimulus_Danger_on_the_Route")
        if belief is not None:
            positions = belief.get_predicate().get_subject()
            route = positions[1]
            result["BL_Route_Status_" + str(route)] = None
        return result

    # ---- beliefs for the reasoner (desire) -> names
    def reasoner_beliefs_for_come_back(self, desire) -> Dict[str, None]:
        result = dict(self.list_for_reasoner_come_back)
        result.update(self._get_green_quality_beliefs_by_desire(desire))
        return result

    def reasoner_beliefs_for_refuel(self, desire) -> Dict[str, None]:
        result = dict(self.list_for_reasoner_come_back)        # Java uses the Come Back list
        result.update(self._get_green_quality_beliefs_by_desire(desire))
        return result

    def reasoner_beliefs_for_destination_city(self, desire) -> Dict[str, None]:
        result = dict(self.list_for_reasoner_destination_city)
        result.update(self._get_green_quality_beliefs_by_desire(desire))
        return result

    def reasoner_beliefs_for_stimulus_danger_on_the_route(self, desire) -> Dict[str, None]:
        result = dict(self.list_for_reasoner_stimulus_danger_on_the_route)
        result.update(self._get_green_quality_beliefs_by_desire(desire))
        return result

    @staticmethod
    def _get_green_quality_beliefs_by_desire(desire) -> Dict[str, None]:
        result: Dict[str, None] = {}
        for green in desire.get_list_green_standing_desire():
            result[green.get_constraint().get_linked_belief().get_name()] = None
        for quality in desire.get_list_quality_standing_desire():
            result[quality.get_constraint().get_linked_belief().get_name()] = None
        return result

    @staticmethod
    def _get_beliefs_by_selected_option(option) -> Dict[str, None]:
        """Names of the beliefs linked to the pre/post-conditions of every action of an option."""
        result: Dict[str, None] = {}
        for action in option.get_plan_actions():
            for pre in action.get_pre_conditions():
                if pre.get_linked_belief() is not None:
                    result[pre.get_subject().get_linked_belief().get_name()] = None
            for post in action.get_post_conditions():
                if post.get_linked_belief() is not None:
                    result[post.get_subject().get_linked_belief().get_name()] = None
        return result


class DesiresRegionsFunctions:
    """Java: TDesires_Regions_Functions."""

    def get_come_back_regions(self, intention, map_beliefs, all_map_regions) -> Dict[str, None]:
        env = map_beliefs.get("BL_Map").get_predicate().get_object_complement()
        bl_dangerous_route = map_beliefs.get("BL_Dangerous_Position_Route")
        dangerous = bl_dangerous_route.get_predicate().get_object_complement()
        specular = env.get_specular_route(dangerous)
        return {"Route_" + str(dangerous): None, "Route_" + str(specular): None,
                bl_dangerous_route.get_name(): None}

    def inhibition_regions_for_destintion_city(self, intention, map_beliefs, map_regions) -> Dict[str, None]:
        """Regions (``Route_n``) of the routes of the selected option and of their specular routes."""
        result: Dict[str, None] = {}
        desire = intention.get_active_desire()
        selected_option_id = intention.get_selected_option_id()
        if selected_option_id >= 0:
            option_simulation = desire.get_list_options()[selected_option_id]
            env = map_beliefs.get("BL_Map").get_predicate().get_object_complement()
            for route in option_simulation.path.routes:
                specular = env.get_specular_route(route)
                if route > -1:
                    result["Route_" + str(route)] = None
                if specular > -1:
                    result["Route_" + str(specular)] = None
        return result

    def reasoner_get_regions_for_come_back(self, map_beliefs) -> Dict[str, None]:
        env = map_beliefs.get("BL_Map").get_predicate().get_object_complement()
        bl_dangerous_route = map_beliefs.get("BL_Dangerous_Position_Route")
        route_position = map_beliefs.get("BL_Position_Route").get_predicate().get_object_complement()
        specular = env.get_specular_route(route_position)
        return {"Route_" + str(route_position): None, "Route_" + str(specular): None,
                bl_dangerous_route.get_name(): None}

    def reasoner_get_regions_for_refuel(self, map_beliefs) -> Dict[str, None]:
        env = map_beliefs.get("BL_Map").get_predicate().get_object_complement()
        route_position = map_beliefs.get("BL_Position_Route").get_predicate().get_object_complement()
        specular = env.get_specular_route(route_position)
        return {"Route_" + str(route_position): None, "Route_" + str(specular): None}

    def inhibition_regions_for_come_back(self, intention, map_beliefs, all_map_regions) -> Dict[str, None]:
        env = map_beliefs.get("BL_Map").get_predicate().get_object_complement()
        bl_dangerous_route = map_beliefs.get("BL_Dangerous_Position_Route")
        dangerous = bl_dangerous_route.get_predicate().get_object_complement()
        specular = env.get_specular_route(dangerous)
        return {"Route_" + str(dangerous): None, "Route_" + str(specular): None,
                bl_dangerous_route.get_name(): None}

    def inhibition_regions_for_refuel(self, intention, map_beliefs, all_map_regions) -> Dict[str, None]:
        env = map_beliefs.get("BL_Map").get_predicate().get_object_complement()
        route_position = map_beliefs.get("BL_Position_Route").get_predicate().get_object_complement()
        if route_position == -1:
            route_position = map_beliefs.get("BL_Next_Position_Route").get_predicate().get_object_complement()
        specular = env.get_specular_route(route_position)
        return {"Route_" + str(route_position): None, "Route_" + str(specular): None}


class DesiresPreconditionsFunctions:
    """Java: TDesires_Precondictions_Functions (not used by the case study wiring)."""

    def __init__(self) -> None:
        self.lists_preconditions_for_desires: Dict[str, Dict[str, None]] = {}

    def sample_compute_preconditions(self, attentional_desire) -> Dict[str, None]:
        """Names of the beliefs in the trigger condition of a desire (and of beliefs used as their subject); remembered per desire.
        """
        pre_conditions: Dict[str, None] = {}
        for belief in attentional_desire.get_trigger_condition().get_beliefs():
            pre_conditions[belief.get_name()] = None
            if isinstance(belief.get_predicate().get_subject(), Belief):
                pre_conditions[belief.get_predicate().get_subject().get_name()] = None
        pre_conditions.pop(None, None)
        self.lists_preconditions_for_desires[attentional_desire.get_name()] = pre_conditions
        return pre_conditions

    def get_destination_city_preconditions(self, attentional_desire, map_beliefs) -> Dict[str, None]:
        temp_list = self.lists_preconditions_for_desires.get(attentional_desire.get_name())
        if temp_list is None:
            temp_list.update(self.sample_compute_preconditions(attentional_desire))   # NPE in Java
        return dict(temp_list)


class DesiresExecutiveFuntions:
    """Java: TDesires_Executive_Funtions (the Come Back means-end function is a stub returning null)."""

    def means_end_function_come_back(self, practical_desire, beliefs, regions, intentions):
        return None


class FunctionsForInhibitionFunction:
    """Java: TFunctions_for_Inhibition_Function."""

    def __init__(self, demo: Any):
        self.demo = demo
        self.common_functions = demo.common_functions
        self.inhibition_function = None
        self.uninhibited_data_changes = 0
        self.desires_preconditions_functions = DesiresPreconditionsFunctions()
        self.desires_beliefs_functions = DesiresBeliefsFunctions()
        self.desires_regions_functions = DesiresRegionsFunctions()

    def get_desires_beliefs_functions(self) -> DesiresBeliefsFunctions:
        return self.desires_beliefs_functions

    def get_desires_regions_functions(self) -> DesiresRegionsFunctions:
        return self.desires_regions_functions

    def get_desires_preconditions_functions(self) -> DesiresPreconditionsFunctions:
        return self.desires_preconditions_functions

    def set_inhibition_function(self, inhibition_function) -> None:
        self.inhibition_function = inhibition_function

    def add_inhibition_functions(self) -> None:
        self.add_lists_for_epistemic_desires()
        self.add_lists_for_practical_desires()
        self.add_important_beliefs()
        self.set_call_back()
        self.set_general_call_back()

    def add_lists_for_epistemic_desires(self) -> None:
        f = self.inhibition_function
        if f is not None:
            f.register_epistemic_belief_inhibition_function(
                "BLTS_Stimulus_Danger_on_the_Route",
                self.desires_beliefs_functions.inhibition_beliefs_for_stimulus_danger_on_the_route)
            f.register_epistemic_region_inhibition_function(
                "BLTS_Stimulus_Danger_on_the_Route", self.desires_regions_functions.get_come_back_regions)

    def add_important_beliefs(self) -> None:
        if self.inhibition_function is not None:
            self.inhibition_function.add_beliefs_to_always_consider("Important_Beliefs", [
                "BL_Current_Time", "BL_Danger_on_the_Route", "BL_Position_City", "BL_Position_Route",
                "BL_Position_Step", "BL_Temporary_Closed_Routes", "ST_Stimulus_Danger_on_the_Route",
                "ST_Stimulus_Irrelevant", "ST_Stimulus_Ok_Correct_Movement", "ST_Stimulus_Route_Status",
                "ST_Stimulus_Temporary_Closed_Route", "BL_Map", "BL_Numbered_City"])

    def add_lists_for_practical_desires(self) -> None:
        """Register the belief and region inhibition functions of the four 'Visit_<city>' desires."""
        f = self.inhibition_function
        if f is not None:
            for city in ("Visit_Paris", "Visit_Frankfurt", "Visit_Rome", "Visit_Cadiz"):
                f.register_practical_belief_inhibition_function(
                    city, self.desires_beliefs_functions.inhibition_beliefs_for_destination_city)
            for city in ("Visit_Paris", "Visit_Frankfurt", "Visit_Rome", "Visit_Cadiz"):
                f.register_practical_region_inhibition_function(
                    city, self.desires_regions_functions.inhibition_regions_for_destintion_city)

    def set_call_back(self) -> None:
        self.demo.agent.get_global_workspace().set_call_back_set_generate_uninhibited_regions_for_intention(
            self.global_workspace_call_back)

    def set_general_call_back(self) -> None:
        self.demo.agent.get_global_workspace().set_general_call_back(self.general_call_back)

    # ---- callbacks (they only feed the "Global Workspace" view in Java)
    def global_workspace_call_back(self, pre_conditions, uninhibited_beliefs, uninhibited_desires,
                                   uninhibited_regions, global_workspace) -> None:
        """Called by the Global Workspace after each update of the uninhibited data: emits a ``gw_update`` event (standing and active desires, selected intention, preconditions, counts). The status is always 'Unfocused' because the Java code reads the first threshold twice.
        """
        self.uninhibited_data_changes += 1
        thresholds = global_workspace.get_saliency_and_attention_thresholds()
        saliency_th = thresholds.get_object_first()
        attention_th = thresholds.get_object_first()          # Java reads First twice (sic)
        standing: List[str] = []
        temp_inhibited = list(global_workspace.get_inhibited_attentional_desires_from_lt())
        active_now = global_workspace.get_unhinibited_desires()
        temp_inhibited = [d for d in temp_inhibited if d not in active_now]
        for desire in temp_inhibited:
            if desire is not None:
                standing.append(desire.get_name())
        active: List[Dict[str, Any]] = []
        for desire in global_workspace.get_unhinibited_desires():
            intention = desire.get_related_intention()
            active.append({"name": desire.get_name(), "saliency": desire.get_saliency(),
                           "intention": intention.get_name() if intention is not None else None})
        selected = global_workspace.get_selected_intentions()
        selected_desire = None
        if len(selected) > 0:
            intention = selected[0]
            if len(intention.get_active_desire().get_list_options()) > 0:
                selected_desire = intention.get_active_desire().get_name()
        status = "Unfocused" if saliency_th == attention_th else "Focused"
        self.demo.event_log.emit(
            "gw_update", n=self.uninhibited_data_changes, agent_status=status, standing_desires=standing,
            active_desires=active, selected_intention_desire=selected_desire,
            preconditions=[b.get_name() for b in pre_conditions],
            n_uninhibited_beliefs=len(uninhibited_beliefs), n_uninhibited_regions=len(uninhibited_regions))

    def general_call_back(self, update_message, gw) -> None:
        """Called by the Global Workspace on every broadcast signal: emits a ``gw_signal`` event (counter, signal name, uninhibited beliefs, selected intention, thresholds).
        """
        selected = gw.get_selected_intentions()
        selected_with_options = None
        if len(selected) > 0:
            first = selected[0]
            if len(first.get_active_desire().get_list_options()) > 0:
                selected_with_options = first.get_name()
        thresholds = gw.get_saliency_and_attention_thresholds()
        self.demo.event_log.emit(
            "gw_signal", n=gw.contatore_di_broadcast,
            signal=update_message.name if update_message is not None else "null",
            uninhibited_beliefs=[b.get_name() for b in gw.get_map_uninhibited_beliefs().values()],
            uninhibited_desires=[d.get_name() for d in gw.get_unhinibited_active_desires()],
            n_uninhibited_regions=len(gw.get_map_uninhibited_regions()),
            intentions=[i.get_name() for i in selected], selected_intention=selected_with_options,
            saliency_threshold=thresholds.get_object_first(), attention_threshold=thresholds.get_object_second())


class FunctionsForRegionInhibitionFunction:
    """Java: TFunctions_for_Region_Inhibition_Function (``Generate_Regions`` is never registered:
    the ``Set_Generate_Unhinibited_Regions_for_Intention`` line is commented out in the source)."""

    def __init__(self, demo: Any):
        self.demo = demo
        self.common_functions = demo.common_functions
        self.inhibition_function = None

    def set_inhibition_function(self, inhibition_function) -> None:
        self.inhibition_function = inhibition_function

    def add_inhibition_functions(self) -> None:
        pass

    def generate_regions(self, intention, map_belief, map_regions) -> Dict[str, Any]:
        """Regions to uninhibit for an intention: by option routes for practical desires, none for epistemic ones.
        """
        from catalina.desires import EpistemicDesire, PracticalDesire
        result: Dict[str, Any] = {}
        desire = intention.get_active_desire()
        if desire is not None:
            if isinstance(desire, PracticalDesire):
                result.update(self.generate_regions_for_destintion_city(intention, map_belief, map_regions))
            elif isinstance(desire, EpistemicDesire):
                result.update(self.generate_regions_for_bl_temporary_closed_routes(intention, map_belief,
                                                                                   map_regions))
            else:
                raise ValueError("Unexpected value: " + str(desire))
        return result

    def generate_regions_for_destintion_city(self, intention, map_beliefs, regions) -> Dict[str, Any]:
        """The region objects of the routes of the selected option and of their specular routes."""
        result: Dict[str, Any] = {}
        by_route: Dict[int, Any] = {}
        for region in regions.values():
            by_route[region.get_route().route_number] = region
        desire = intention.get_active_desire()
        selected_option_id = intention.get_selected_option_id()
        if selected_option_id >= 0:
            option_simulation = desire.get_list_options()[selected_option_id]
            env = map_beliefs.get("BL_Map").get_predicate().get_object_complement()
            for route in option_simulation.path.routes:
                specular = env.get_specular_route(route)
                region = by_route.get(route)
                specular_region = by_route.get(specular)
                if region is not None:
                    result[region.get_name()] = region
                if specular_region is not None:
                    result[specular_region.get_name()] = specular_region
        return result

    def generate_regions_for_bl_temporary_closed_routes(self, intention, map_beliefs, map_regions) -> Dict[str, Any]:
        return {}

    def generate_regions_for_come_back(self, intention, map_beliefs, map_regions) -> Dict[str, Any]:
        return {}
