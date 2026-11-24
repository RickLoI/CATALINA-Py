"""Means-end reasoner, desire filtering and deliberation of the case study.

Java: TFunctions_for_Means_End_Reasoner, TFunctions_for_Filtering_Desires_Function,
TFunctions_for_Deliberation_Process.

Option generation (``Reasoner_Function_for_*``) builds, for each candidate path, the action list
``Initialize_Way`` / ``GO_TO_Route`` / ``GO_TO_Step`` (or ``Reverse_Direction``, ``Declare_the_Refuel``,
``Refuelling``) with position pre/post-conditions. Local variables of the Java code that are
computed and never read (``TPosition_Coords`` objects, ``step_position`` ...) are not reproduced.

Java behaviour kept on purpose:
* ``All_Routes.get(-1)`` raises in ``Come_Back`` / ``Refuel`` (the car must be on a route).
* ``Refuel`` overwrites the step with the *next* step before searching, and its specular route
  and step come from the *current* position (so they are -1 / 0 when the car is in a city).
* ``Sort_Selected_Intentions`` sorts the list passed by the caller in place and drops the
  intentions without desire.
* the Velocity quality constraint divides the target by 39 before comparing speeds.
"""
from __future__ import annotations

import math
from datetime import timedelta
from functools import cmp_to_key
from typing import Any, Dict, List, Optional

from catalina.enums import TypeRelationship
from catalina.model import Predicate
from catalina.plan import Action, Intention

from .domain import TCity, TTypeQualityDesire
from .environment import OptionSimulation, PlanSimulation


def _pred(name, belief, value) -> Predicate:
    return Predicate(name, belief, TypeRelationship.is_, value)


class FunctionsForMeansEndReasoner:
    """Means-end reasoning of the case study: builds the options (plans over the map) of each kind of desire.
    Registered on the Reasoner by ``add_functions_to_means_end_reasoner``.
    """
    def __init__(self, demo: Any):
        from .functions_inhibition import DesiresExecutiveFuntions
        self.demo = demo
        self.common_functions = demo.common_functions
        self.desires_executive_funtions = DesiresExecutiveFuntions()

    def get_desires_executive_funtions(self):
        return self.desires_executive_funtions

    def add_functions_to_means_end_reasoner(self, reasoner=None) -> None:
        agent = self.demo.agent
        agent.reasoner_register_epistemic_function("BLTS_Stimulus_Danger_on_the_Route",
                                                   self.reasoner_function_for_stimulus_danger_on_the_route)
        for city in ("Visit_Paris", "Visit_Frankfurt", "Visit_Rome", "Visit_Cadiz"):
            agent.reasoner_register_practical_function(city, self.reasoner_function_for_destination_city)

    def add_beliefs_to_means_end_reasoner(self, reasoner=None) -> None:
        pass

    # ------------------------------------------------------------------ epistemic
    def reasoner_function_for_stimulus_danger_on_the_route(self, epistemic_desire, beliefs, regions,
                                                           intentions, planner) -> List[Any]:
        """Epistemic desire 'danger on the route': one option with two actions, 'Ask Danger Type on the road'
        and 'Decide_To_Continue_or_Not'.
        """
        stimulus = epistemic_desire.get_belief()
        predicate = stimulus.get_predicate()
        planner.get_plans(epistemic_desire, None)
        first = Action()
        first.set_action_name("Ask Danger Type on the road")
        first.get_params().append(predicate.get_subject())
        second = Action()
        second.set_action_name("Decide_To_Continue_or_Not")
        return [OptionSimulation([first, second], predicate, None, None)]

    # ------------------------------------------------------------------ destination city
    def reasoner_function_for_destination_city(self, practical_desire, beliefs, regions, intentions,
                                               planner) -> List[Any]:
        """Options for 'Visit <city>': one option per simple path (DFS) from the current city, or from the
        damaged route if the car is already on one. Each option is the list of Initialize_Way / GO_TO_Route
        / GO_TO_Step actions with pre/post-conditions on the position beliefs, the quality weights of the
        path and the expected satisfaction time. Per-route step data is computed once and shared by the
        paths (the plan predicates are read-only).
        """
        cf = self.common_functions
        temp_beliefs = list(practical_desire.get_final_state().get_beliefs())
        belief_destination = cf.get_array_beliefs_by_type(temp_beliefs, "BLT_Destination_City")[0]
        city_name = str(belief_destination.get_predicate().get_object_complement())
        destination_city = TCity.value_of(city_name)
        bl_position_city = beliefs.get("BL_Position_City")
        city_number = bl_position_city.get_predicate().get_object_complement()
        current_city = TCity.values()[city_number]
        env = beliefs.get("BL_Map").get_predicate().get_object_complement()
        current_time = beliefs.get("BL_Current_Time").get_predicate().get_object_complement()
        bl_position_route = beliefs.get("BL_Position_Route")
        temp_route_number = bl_position_route.get_predicate().get_object_complement()
        bl_position_step = beliefs.get("BL_Position_Step")
        temp_step_number = bl_position_step.get_predicate().get_object_complement()
        temp_specular_step_number = 0
        temp_specular_route_number = 0
        start_new_travel = True
        if temp_step_number == 0:
            paths = env.find_all_paths(current_city, destination_city)
        else:
            start_new_travel = False
            temp_specular_step_number = env.get_specular_step_in_route(temp_route_number, temp_step_number)
            temp_specular_route_number = env.get_specular_route(temp_route_number)
            paths = env.find_all_paths_from_a_damaged_route(temp_route_number, temp_step_number,
                                                            destination_city)
        end_time = practical_desire.get_final_state().get_temporal_operator().get_end_time()
        options: List[Any] = []
        _cache: dict = {}

        def _pred(name, belief, value, _c=_cache):     # plan predicates are read-only: share them
            key = (name, id(belief), value)
            p = _c.get(key)
            if p is None:
                p = _c[key] = Predicate(name, belief, TypeRelationship.is_, value)
            return p

        route_specs: dict = {}

        def build_spec(route_number):
            """Per-route step data (pure function of the route and the car position): cached across paths."""
            a_route = env.route_at(route_number)
            rounds_time = a_route.get_total_rounds()
            departure = a_route.get_departure()
            destination = a_route.get_destination()
            position_start_step = temp_step_number
            route_speed = a_route.get_route_speed()
            steps_number_on_route = a_route.get_steps_number()
            other_step = 0 if start_new_travel else 1
            spec = []
            for _step in range(1, rounds_time + 1):
                other_step += 1
                if other_step == 1:
                    function_to_invoke = "GO_TO_Route"
                    position_start_city = departure.ordinal
                    position_start_route = -1
                    position_start_step = 0
                    position_end_city = departure.ordinal
                    position_end_step = position_start_step + route_speed
                else:
                    function_to_invoke = "GO_TO_Step"
                    position_start_city = departure.ordinal
                    position_start_route = route_number
                    position_start_step += route_speed
                    if other_step == 2 and not start_new_travel:
                        if temp_specular_route_number == position_start_route:
                            position_start_step = temp_specular_step_number
                    position_end_city = departure.ordinal
                    position_end_step = position_start_step + route_speed
                if position_end_step > steps_number_on_route:
                    position_end_city = destination.ordinal
                    position_end_route = -1
                    position_end_step = 0
                else:
                    position_end_route = route_number
                bl_pre_status = beliefs.get("BL_Route_Status_" + str(position_start_route))
                bl_post_status = beliefs.get("BL_Route_Status_" + str(position_end_route))
                spec.append((
                    function_to_invoke,
                    (position_start_city, position_start_route, position_start_step),
                    (position_end_city, position_end_route, position_end_step),
                    _pred("Position_City", bl_position_city, position_start_city),
                    _pred("Position_Route", bl_position_route, position_start_route),
                    _pred("Position_Step", bl_position_step, position_start_step),
                    None if bl_pre_status is None else _pred(
                        "BL_Route_Status_" + str(position_start_route), bl_pre_status, "Green"),
                    _pred(None, bl_position_city, position_end_city),
                    _pred(None, bl_position_route, position_end_route),
                    _pred(None, bl_position_step, position_end_step),
                    None if bl_post_status is None else _pred(
                        "BL_Route_Status_" + str(position_end_route), bl_post_status, "Green")))
            return spec

        for path in paths:
            first_action = True
            actions: List[Action] = []
            action_id = 0
            for route_number in path.routes:
                spec = route_specs.get(route_number)
                if spec is None:
                    spec = route_specs[route_number] = build_spec(route_number)
                for (function_to_invoke, start, end, pre_city, pre_route, pre_step, pre_status,
                     post_city, post_route, post_step, post_status) in spec:
                    action_id += 1
                    params: List[Any] = []
                    if function_to_invoke == "GO_TO_Route":
                        initialize = Action()
                        initialize.set_action_name("Initialize_Way")
                        initialize.set_id(action_id)
                        params.extend([end[0], end[1], end[2]])
                        if first_action:
                            first_action = False
                            initialize.add_pre_condition(pre_city)
                            initialize.add_pre_condition(pre_route)
                            initialize.add_pre_condition(pre_step)
                            params.append(practical_desire.get_name())
                            params.append(end_time)
                        initialize.set_params(params)
                        actions.append(initialize)
                        action_id += 1
                        params = []
                    action = Action()
                    action.set_id(action_id)
                    params.append(route_number)
                    action.set_params(params)
                    action.add_pre_condition(pre_city)
                    action.add_pre_condition(pre_route)
                    action.add_pre_condition(pre_step)
                    if pre_status is not None:
                        action.add_pre_condition(pre_status)
                    action.add_post_condition(post_city)
                    action.add_post_condition(post_route)
                    action.add_post_condition(post_step)
                    if post_status is not None:
                        action.add_post_condition(post_status)
                    action.set_action_name(function_to_invoke)
                    actions.append(action)
            option = OptionSimulation(actions, None, 0.0, path.total_weights)
            option.path.copy_plan(path)
            minute_of_hours = int(path.path_time)
            minutes = int((path.path_time - minute_of_hours) * 60) + minute_of_hours * 60
            option.set_satisfied_time(current_time + timedelta(minutes=minutes))
            option.get_plan_actions()[0].get_params().append(option.get_satisfied_time())
            options.append(option)
        return options

    # ------------------------------------------------------------------ come back
    def reasoner_function_for_come_back_to_city(self, practical_desire, beliefs, regions, intentions,
                                                planner) -> List[Any]:
        """Options for the come-back desire: Reverse_Direction followed by GO_TO_Step actions back along the
        route to the city the car left (Java quirks kept, see the module docstring).
        """
        bl_position_city = beliefs.get("BL_Position_City")
        city_position = bl_position_city.get_predicate().get_object_complement()
        city_name = TCity.values()[city_position]
        city_number = city_position
        env = beliefs.get("BL_Map").get_predicate().get_object_complement()
        current_time = beliefs.get("BL_Current_Time").get_predicate().get_object_complement()
        bl_position_route = beliefs.get("BL_Position_Route")
        temp_route_number = bl_position_route.get_predicate().get_object_complement()
        bl_position_step = beliefs.get("BL_Position_Step")
        temp_step_number = bl_position_step.get_predicate().get_object_complement()
        specular_route_number = env.get_specular_route(temp_route_number)
        specular_step_number = env.get_specular_step_in_route(temp_route_number, temp_step_number)
        a_route = env.route_at(temp_route_number)               # raises when the car is in a city
        route_speed = a_route.get_route_speed()
        steps_number_on_route = a_route.get_steps_number()
        rounds_time = int(math.ceil(float(steps_number_on_route - temp_step_number) / route_speed))
        actions: List[Action] = []
        action_id = 1
        action = Action()
        action.set_action_name("Reverse_Direction")
        action.set_id(action_id)
        action.set_params([specular_route_number, city_number, specular_route_number, specular_step_number])
        action.add_pre_condition(_pred("Position_City", bl_position_city, city_number))
        action.add_pre_condition(_pred("Position_Route", bl_position_route, temp_route_number))
        action.add_pre_condition(_pred("Position_Step", bl_position_step, temp_step_number))
        action.add_post_condition(_pred(None, bl_position_city, city_number))
        action.add_post_condition(_pred(None, bl_position_route, specular_route_number))
        action.add_post_condition(_pred(None, bl_position_step, specular_step_number))
        actions.append(action)
        position_start_step = specular_step_number - route_speed
        for _step in range(1, rounds_time + 1):
            position_start_step += route_speed
            position_end_city = city_position
            position_end_route = specular_route_number
            position_end_step = position_start_step + route_speed
            if position_end_step > steps_number_on_route:
                position_end_city = city_position
                position_end_route = -1
                position_end_step = 0
            else:
                position_end_route = specular_route_number
            action_id += 1
            step_action = Action()
            step_action.set_id(action_id)
            step_action.set_params([specular_route_number])
            step_action.add_pre_condition(_pred("Position_City", bl_position_city, city_position))
            step_action.add_pre_condition(_pred("Position_Route", bl_position_route, specular_route_number))
            step_action.add_pre_condition(_pred("Position_Step", bl_position_step, position_start_step))
            step_action.add_post_condition(_pred(None, bl_position_city, position_end_city))
            step_action.add_post_condition(_pred(None, bl_position_route, position_end_route))
            step_action.add_post_condition(_pred(None, bl_position_step, position_end_step))
            step_action.set_action_name("GO_TO_Step")
            actions.append(step_action)
        quality = {TTypeQualityDesire.Motor: a_route.get_route_locomotive(),
                   TTypeQualityDesire.Panorama: a_route.get_route_panorama(),
                   TTypeQualityDesire.Speed: float(a_route.get_route_speed())}
        option = OptionSimulation(actions, None, 0.0, quality)
        plan = PlanSimulation()
        plan.insert_path_by_routes([city_name], [specular_route_number], quality, float(rounds_time))
        option.path.copy_plan(plan)
        minutes = int(plan.path_time) * 60
        option.set_satisfied_time(current_time + timedelta(minutes=minutes))
        return [option]

    # ------------------------------------------------------------------ refuel
    def reasoner_function_for_refuel(self, practical_desire, beliefs, regions, intentions, planner) -> List[Any]:
        """Options for the refuel desire: Declare_the_Refuel, Reverse_Direction, GO_TO_Step actions to the
        nearest city and Refuelling (Java overwrites the step with the next step, kept).
        """
        bl_position_city = beliefs.get("BL_Position_City")
        city_position = bl_position_city.get_predicate().get_object_complement()
        city_name = TCity.values()[city_position]
        destination_city = city_name
        city_number = city_position
        env = beliefs.get("BL_Map").get_predicate().get_object_complement()
        current_time = beliefs.get("BL_Current_Time").get_predicate().get_object_complement()
        bl_position_route = beliefs.get("BL_Position_Route")
        temp_route_number = bl_position_route.get_predicate().get_object_complement()
        bl_position_step = beliefs.get("BL_Position_Step")
        bl_next_position_step = beliefs.get("BL_Next_Position_Step")
        temp_next_step_number = bl_next_position_step.get_predicate().get_object_complement()
        temp_step_number = temp_next_step_number                       # Java overwrites the step
        bl_next_position_route = beliefs.get("BL_Next_Position_Route")
        temp_next_route_number = bl_next_position_route.get_predicate().get_object_complement()
        temp_next_city_number = beliefs.get("BL_Next_Position_City").get_predicate().get_object_complement()
        specular_route_number = env.get_specular_route(temp_route_number)
        specular_step_number = env.get_specular_step_in_route(temp_route_number, temp_step_number)
        time = 0
        planner_predicates = [_pred("Position_City", bl_position_city, city_number),
                              _pred("Position_Route", bl_position_route, temp_route_number),
                              _pred("Position_Step", bl_position_step, temp_step_number)]
        planner_actions = list(planner.get_plans(practical_desire, planner_predicates))
        actions: List[Action] = []
        if temp_route_number == -1:
            temp_route_number = bl_next_position_route.get_predicate().get_object_complement()
        a_route = env.route_at(temp_route_number)
        route_speed = a_route.get_route_speed()
        steps_number_on_route = a_route.get_steps_number()
        rounds_time = int(math.ceil(float(steps_number_on_route - temp_step_number) / route_speed))
        if len(planner_actions) > 0:
            actions.extend(planner_actions)
        else:
            position_start_step = temp_step_number
            position_start_route = temp_route_number
            position_start_city = city_number
            position_end_step = specular_step_number
            position_end_route = specular_route_number
            position_end_city = city_number
            action_id = 1
            declare = Action()
            declare.set_action_name("Declare_the_Refuel")
            declare.set_id(action_id)
            declare.set_params([destination_city.ordinal, position_start_city, position_start_route,
                                position_start_step, position_end_city, position_end_route, position_end_step,
                                temp_next_city_number, temp_next_route_number, temp_next_step_number])
            declare.add_pre_condition(_pred("Position_City", bl_position_city, position_start_city))
            declare.add_pre_condition(_pred("Position_Route", bl_position_route, position_start_route))
            declare.add_pre_condition(_pred("Position_Step", bl_position_step, position_start_step))
            actions.append(declare)
            action_id += 1
            reverse = Action()
            reverse.set_action_name("Reverse_Direction")
            reverse.set_id(action_id)
            reverse.set_params([specular_route_number, position_start_city, position_start_route,
                                position_start_step])
            reverse.add_post_condition(_pred(None, bl_position_city, city_number))
            reverse.add_post_condition(_pred(None, bl_position_route, specular_route_number))
            reverse.add_post_condition(_pred(None, bl_position_step, specular_step_number))
            actions.append(reverse)
            position_start_step = specular_step_number - route_speed
            for _step in range(1, rounds_time + 1):
                time += 1
                position_start_step += route_speed
                position_end_city = city_position
                position_end_route = specular_route_number
                position_end_step = position_start_step + route_speed
                if position_end_step > steps_number_on_route:
                    position_end_city = city_position
                    position_end_route = -1
                    position_end_step = 0
                else:
                    position_end_route = specular_route_number
                action_id += 1
                step_action = Action()
                step_action.set_id(action_id)
                step_action.set_params([specular_route_number])
                step_action.add_pre_condition(_pred("Position_City", bl_position_city, city_position))
                step_action.add_pre_condition(_pred("Position_Route", bl_position_route, specular_route_number))
                step_action.add_pre_condition(_pred("Position_Step", bl_position_step, position_start_step))
                step_action.add_post_condition(_pred(None, bl_position_city, position_end_city))
                step_action.add_post_condition(_pred(None, bl_position_route, position_end_route))
                step_action.add_post_condition(_pred(None, bl_position_step, position_end_step))
                step_action.set_action_name("GO_TO_Step")
                actions.append(step_action)
            time += 1
            action_id += 1
            refuelling = Action()
            refuelling.set_action_name("Refuelling")
            refuelling.set_id(action_id)
            refuelling.set_params([100, city_name.ordinal])
            actions.append(refuelling)
        quality = {TTypeQualityDesire.Motor: a_route.get_route_locomotive(),
                   TTypeQualityDesire.Panorama: a_route.get_route_panorama(),
                   TTypeQualityDesire.Speed: float(a_route.get_route_speed())}
        option = OptionSimulation(actions, None, 0.0, quality)
        plan = PlanSimulation()
        plan.insert_path_by_routes([city_name], [specular_route_number], quality, float(rounds_time))
        option.path.copy_plan(plan)
        option.set_satisfied_time(current_time + timedelta(minutes=time * 60))
        return [option]


class FunctionsForFilteringDesiresFunction:
    """Java: TFunctions_for_Filtering_Desires_Function."""

    def __init__(self, demo: Any):
        self.demo = demo
        self.common_functions = demo.common_functions

    def add_function_to_filter_process(self, reasoner) -> None:
        reasoner.register_green_filtering_function("GDT_Limited_Pollution_to",
                                                   self.apply_green_filter_limited_pollution_to_0_8)
        reasoner.set_quality_desire_filtering_process(self.apply_quality_filter)

    def apply_green_filter_limited_pollution_to_0_8(self, green_desire, desire, beliefs, regions,
                                                    intentions) -> List[Any]:
        """Green filter 'Limited_Pollution': keeps the options whose average motor value respects the desire's
        constraint (minor, minor_equal, ...).
        """
        current_options = desire.get_list_options()
        result: List[Any] = []
        predicate = green_desire.get_constraint()
        limit = predicate.get_object_complement()
        relationship = predicate.get_relationship()
        if relationship == TypeRelationship.minor:
            for option in current_options:
                if option.path.total_weights[TTypeQualityDesire.Motor] < limit:
                    result.append(option)
        elif relationship == TypeRelationship.minor_equal:
            for option in current_options:
                if option.path.total_weights[TTypeQualityDesire.Motor] <= limit:
                    result.append(option)
        return result

    def apply_quality_filter(self, desire, beliefs, regions, intentions) -> List[Any]:
        """Quality filter: remove the options that exceed each quality constraint (by decreasing saliency of
        the quality desires) and sort the rest with the combined comparators.
        """
        result = list(desire.get_list_options())
        qualities = list(desire.get_list_quality_standing_desire())
        qualities.sort(key=lambda d: d.get_saliency(), reverse=True)     # stable, like Java
        comparator = None
        for quality_desire in qualities:
            type_quality = quality_desire.get_type_quality_goal()
            value = quality_desire.get_constraint().get_object_complement()
            self._remove_options_that_exceed_quality_constraints(result, type_quality, value)
            current = self._create_comparator_by_quality(type_quality, value)
            if comparator is None:
                comparator = current
            else:
                comparator = self._then_comparing(comparator, current)
        if comparator is not None:
            result.sort(key=cmp_to_key(comparator))
        return result

    @staticmethod
    def _then_comparing(first, second):
        def cmp(a, b):
            r = first(a, b)
            return r if r != 0 else second(a, b)
        return cmp

    @staticmethod
    def _double_compare(a: float, b: float) -> int:
        return -1 if a < b else (1 if a > b else 0)

    def _create_comparator_by_quality(self, type_quality: str, value):
        """Comparator of two options for a quality desire (panorama: higher is better; velocity: closer to the
        target is better).
        """
        if type_quality == "QDT_Panorama_is_Great":
            def cmp_panorama(o1, o2) -> int:
                """Order two options by panorama value, highest first (0 when the value is missing)."""
                try:
                    v1 = o1.get_quality_list().get(TTypeQualityDesire.Panorama)
                    v2 = o2.get_quality_list().get(TTypeQualityDesire.Panorama)
                    v1 = 0.0 if v1 is None else v1
                    v2 = 0.0 if v2 is None else v2
                    return self._double_compare(v2, v1)
                except Exception:       # noqa: BLE001 - same catch-all as Java
                    return 0
            return cmp_panorama
        if type_quality == "QDT_Velocity_is_Moderate":
            target = float(value)

            def cmp_velocity(o1, o2) -> int:
                """Order two options by distance of their speed from the target."""
                try:
                    v1 = o1.get_quality_list().get(TTypeQualityDesire.Speed)
                    v2 = o2.get_quality_list().get(TTypeQualityDesire.Speed)
                    v1 = target if v1 is None else v1
                    v2 = target if v2 is None else v2
                    return self._double_compare(abs(v1 - target), abs(v2 - target))
                except Exception:       # noqa: BLE001
                    return 0
            return cmp_velocity
        return lambda o1, o2: 0

    @staticmethod
    def _remove_options_that_exceed_quality_constraints(options: List[Any], type_quality: str, value) -> None:
        """In-place removal of the options above the quality limit (for velocity the target is divided by 39, a
        Java quirk kept).
        """
        if type_quality == "QDT_Velocity_is_Moderate":
            limit = float(value) / 39
            keep = []
            for option in options:
                try:
                    val = option.get_quality_list().get(TTypeQualityDesire.Speed)
                    remove = val is not None and val > limit
                except Exception:       # noqa: BLE001
                    remove = False
                if not remove:
                    keep.append(option)
            options[:] = keep


class FunctionsForDeliberationProcess:
    """Java: TFunctions_for_Deliberation_Process."""

    def __init__(self, demo: Any):
        self.demo = demo
        self.common_functions = demo.common_functions

    def add_function_to_means_end_reasoner(self, reasoner) -> None:
        reasoner.set_deliberation_process_function(self.deliberation_process_function)

    def deliberation_process_function(self, active_desires, beliefs, regions, list_intentions) -> List[Any]:
        """Choose the intentions among the active desires not yet in an intention, by decreasing saliency: a
        desire without options gets an intention with no option (and "I have no option for Desire: X" is
        printed); the first one with options gets an intention on option 0; the existing intentions are
        appended, sorted.
        """
        selected: List[Any] = []
        desires_in_intentions = [i.get_active_desire() for i in list_intentions]
        to_promote = [d for d in active_desires if d not in desires_in_intentions]
        to_promote.sort(key=lambda d: d.get_saliency(), reverse=True)
        number_to_pursue = 1
        counter = 0
        for desire in to_promote:
            if len(desire.get_list_options()) < 1:
                intention = Intention("", desire, -1)
                desire.set_related_intention(intention)
                intention.set_desire(desire)
                selected.append(intention)
                self.common_functions.print("I have no option for Desire: " + desire.get_name())
            else:
                if counter < number_to_pursue:
                    intention = Intention("Int_" + desire.get_name(), desire, 0)
                    desire.set_related_intention(intention)
                    intention.set_desire(desire)
                    selected.append(intention)
                    counter += 1
        selected.extend(self._sort_selected_intentions(list_intentions))
        return selected

    @staticmethod
    def _sort_selected_intentions(intentions: List[Any]) -> List[Any]:
        """Order intentions by saliency of their desire, highest first, intentions without desire last."""
        def cmp(i1, i2) -> int:
            """Order two intentions by the saliency of their desires, highest first (no desire last)."""
            d1, d2 = i1.get_active_desire(), i2.get_active_desire()
            if d1 is None and d2 is None:
                return 0
            if d1 is None:
                return 1
            if d2 is None:
                return -1
            s1, s2 = d1.get_saliency(), d2.get_saliency()
            return -1 if s2 < s1 else (1 if s2 > s1 else 0)

        intentions.sort(key=cmp_to_key(cmp))             # in place, like Java
        temp: Optional[Any] = None
        new_intentions: List[Any] = []
        for intention in intentions:
            desire = intention.get_active_desire()
            if desire is not None:
                if len(desire.get_list_options()) > 0:
                    if temp is None:
                        temp = intention
                else:
                    new_intentions.append(intention)
        if temp is not None:
            new_intentions.insert(0, temp)
        return new_intentions
