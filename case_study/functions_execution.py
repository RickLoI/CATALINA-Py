"""Action execution of the case study (Java: TFunctions_for_Option_Execution).

Registered action names: ``Ask Danger Type on the road``, ``GO_TO_Route``, ``GO_TO_Step``,
``Initialize_Way``, ``Wait``, ``Change_Direction``, ``Reverse_Direction``,
``Decide_To_Continue_or_Not``, ``Refuelling``, ``Declare_the_Refuel``.

``Move_Car_Slowly`` waits on the demo clock (simulated seconds), ``Global_Time_to_Move`` = 1 s per
step as in Java.

Java behaviour kept on purpose:
* ``Update_Routes`` decrements a *local copy* of each duration, so only closures with duration 1
  ever end; removing while iterating raises ``ConcurrentModificationException`` when the iteration
  has not ended (reproduced in Java ``HashMap`` order), and the belief value is mutated in place.
  It reports the end through ``BLT_Temporary_Closed_Routes`` (a type name, not a belief name).
* In ``GO_TO_Route`` / ``GO_TO_Step`` the ``Previous_Position_Step`` is the loop-incremented start step.
* ``Execute_Decision`` never stores the ``Beliefs_To_Change`` it computes in the result; the
  ``BL_Come_Back_to_City`` belief is instead mutated in place by ``Rise_Come_Back_Desire``.
* ``Execute_Change_Direction`` returns a failed (empty) result.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List

from catalina.desire_data import PracticalDesireData
from catalina.desires import PracticalDesire
from catalina.enums import TypeTemporalOperator
from catalina.formula import TemporalOperator, TemporalPropositionalFormula
from catalina.handlers import ActionExecutionResult

from .domain import TCity
from .javacompat import ConcurrentModificationError, hashmap_key_order


def _me(kind: str, value: Any) -> List[Any]:
    return [kind, value, "Me"]


class FunctionsForOptionExecution:
    """The ten action functions of the case study (Java: TFunctions_for_Option_Execution), registered in Action
    Control by action name. Each returns an ``ActionExecutionResult`` with the beliefs to change.
    """
    def __init__(self, demo: Any):
        self.demo = demo
        self.common_functions = demo.common_functions
        self.global_time_to_move = 1.0
        self.response_sended = False
        self.string_response_sended = ""
        self.belief_inhibition_functions = demo.functions_for_belief_inhibition_function
        self.practical_desire_number = 0
        self.contatore = 0

    def add_function_to_switching_function(self, action_control) -> None:
        """Register the ten action functions (Ask Danger Type, GO_TO_Route, GO_TO_Step, Initialize_Way, Wait,
        Change_Direction, Reverse_Direction, Decide_To_Continue_or_Not, Refuelling, Declare_the_Refuel).
        """
        reg = action_control.register_plan_execution_funtion_to_execute
        reg("Ask Danger Type on the road", self.execute_ask_danger_type_on_the_road)
        reg("GO_TO_Route", self.execute_movement_go_to_route)
        reg("GO_TO_Step", self.execute_movement_go_to_step)
        reg("Initialize_Way", self.execute_initialize_way)
        reg("Wait", self.execute_wait)
        reg("Change_Direction", self.execute_change_direction)
        reg("Reverse_Direction", self.execute_reverse_direction)
        reg("Decide_To_Continue_or_Not", self.execute_decision)
        reg("Refuelling", self.execute_refuelling)
        reg("Declare_the_Refuel", self.execute_declare_the_refuel)

    # ---------------------------------------------------------------- simple actions
    def execute_initialize_way(self, global_workspace, action, beliefs_cloned) -> ActionExecutionResult:
        """Set the Next_Position beliefs (and, for the first action of a travel, the previous travel's
        intention and maximum satisfaction time).
        """
        result = ActionExecutionResult()
        params = action.get_params()
        changes: Dict[str, Any] = {
            "BL_Next_Position_City": ["Object_Complement", params[0]],
            "BL_Next_Position_Route": ["Object_Complement", params[1]],
            "BL_Next_Position_Step": ["Object_Complement", params[2]],
        }
        if len(params) > 3:
            desire_name = params[3]
            max_satisfaction_time = params[4]
            changes["BL_Previous_Travel_Intention_Max_Satisfaction_Time"] = ["Subject", desire_name]
            changes["BL_Previous_Travel_Intention_Max_Satisfaction_Time"] = [
                "Object_Complement", max_satisfaction_time]          # replaces the previous entry
        result.set_result(True)
        result.set_beliefs_to_change(changes)
        return result

    def execute_wait(self, global_workspace, action, map_beliefs) -> ActionExecutionResult:
        """Wait action: only updates the temporary closed routes and the current time."""
        result = ActionExecutionResult()
        changes: Dict[str, Any] = {}
        changes.update(self.update_routes(action, map_beliefs))
        changes.update(self.update_current_time(action, map_beliefs))
        self.common_functions.println("Execute_Wait Execute_Wait")
        result.set_result(True)
        result.set_beliefs_to_change(changes)
        return result

    def execute_ask_danger_type_on_the_road(self, global_workspace, action, map_beliefs) -> ActionExecutionResult:
        """The car found a closed route: print the messages and query the traffic control
        (``danger_query_simulation``) about the type and duration of the danger.
        """
        cf = self.common_functions
        result = ActionExecutionResult()
        cf.print_colored_text("----------------------", 3)
        cf.print_colored_text("+++ I found the route closed!! +++", 3)
        cf.print_colored_text("+++ I stop and ask for some information!! +++", 3)
        cf.print_colored_text("This is a simulation of a virtual Frontal Camera...", 3)
        positions = action.get_params()[0]
        _ = (positions[0], positions[1], positions[2])               # Java reads them, then overwrites
        city_position = map_beliefs.get("BL_Position_City").get_predicate().get_object_complement()
        route_position = map_beliefs.get("BL_Position_Route").get_predicate().get_object_complement()
        step_position = map_beliefs.get("BL_Position_Step").get_predicate().get_object_complement()
        real_positions = [city_position, route_position, step_position]
        dangerous_route_position = route_position
        if route_position == -1:
            dangerous_route_position = map_beliefs.get(
                "BL_Next_Position_Route").get_predicate().get_object_complement()
        real_positions.append(dangerous_route_position)
        beliefs_to_wait: Dict[str, Any] = {}
        bl_closed_duration = map_beliefs.get("BL_Temporary_Closed_Duration")
        beliefs_to_wait["BL_Temporary_Closed_Duration"] = bl_closed_duration.get_time_stamp()
        tcs = self.demo.perception_processing_functions.virtual_tcs
        tcs.danger_query_simulation(real_positions)
        result.set_result(True)
        result.set_beliefs_to_change({})
        result.set_beliefs_to_wait(beliefs_to_wait)
        return result

    def execute_reverse_direction(self, global_workspace, action, map_beliefs) -> ActionExecutionResult:
        """Turn back: set the position beliefs to the end positions of the action's post-conditions."""
        result = ActionExecutionResult()
        post = action.get_post_conditions()
        end_city = post[0].get_object_complement()
        end_route = post[1].get_object_complement()
        end_step = post[2].get_object_complement()
        self.common_functions.println("I change direction of the route to go back")
        result.set_result(True)
        result.set_beliefs_to_change({
            "BL_Position_City": _me("Object_Complement", end_city),
            "BL_Position_Route": _me("Object_Complement", end_route),
            "BL_Position_Step": _me("Object_Complement", end_step),
        })
        return result

    # ---------------------------------------------------------------- movement
    def _arrival(self, changes: Dict[str, Any], map_beliefs, end_city: int) -> None:
        """Mark the city as visited and print 'I'm arrived in <city>' (plus the satisfied-desire message when
        it is the destination city belief).
        """
        cf = self.common_functions
        city_name = TCity.values()[end_city].name
        changes["BL_City_Visited_" + city_name] = _me("Object_Complement", True)
        cf.print("I'm arrived in " + city_name)
        for belief in map_beliefs.values():
            if belief.get_type_belief() == "BLT_Destination_City":
                if belief.get_predicate().get_object_complement() == city_name:
                    cf.print("Practical Desire satisfied! I arrived in: " + city_name)

    def _position_changes(self, start_city, start_route, start_step, end_city, end_route, end_step,
                          action, map_beliefs) -> Dict[str, Any]:
        """Beliefs to change for a movement: new and previous position, closed routes and current time."""
        changes: Dict[str, Any] = {
            "BL_Position_City": _me("Object_Complement", end_city),
            "BL_Position_Route": _me("Object_Complement", end_route),
            "BL_Position_Step": _me("Object_Complement", end_step),
            "BL_Previous_Position_City": _me("Object_Complement", start_city),
            "BL_Previous_Position_Route": _me("Object_Complement", start_route),
            "BL_Previous_Position_Step": _me("Object_Complement", start_step),
        }
        changes.update(self.update_routes(action, map_beliefs))
        changes.update(self.update_current_time(action, map_beliefs))
        return changes

    def execute_movement_go_to_route(self, global_workspace, action, map_beliefs) -> ActionExecutionResult:
        """Print 'I enter Route: [n]' and drive the car step by step from the action's start step to its end
        step (to the end of the route when both are equal); when the action ends the route, arrive in the
        city.
        """
        result = ActionExecutionResult()
        pre = action.get_pre_conditions()
        post = action.get_post_conditions()
        start_city = pre[0].get_object_complement()
        start_route = pre[1].get_object_complement()
        start_step = pre[2].get_object_complement()
        end_city = post[0].get_object_complement()
        end_route = post[1].get_object_complement()
        end_step = post[2].get_object_complement()
        env = map_beliefs.get("BL_Map").get_predicate().get_object_complement()
        route_for_map = action.get_params()[0] if end_route < 0 else end_route
        self.common_functions.print("I enter Route: " + str(action.get_params()))
        env.get_route(route_for_map)
        panel = self.demo.map_panel
        points = panel.ruotes_coords.get(route_for_map)
        time_to_move = self.global_time_to_move
        if start_step < end_step:
            while start_step < end_step:
                start_step += 1
                panel.move_car_slowly(points[start_step - 1], time_to_move, route_for_map, start_step)
        elif start_step == end_step:
            route = env.route_at(route_for_map)
            while start_step < route.get_steps_number():
                start_step += 1
                panel.move_car_slowly(points[start_step - 1], time_to_move, route_for_map, start_step)
        changes = self._position_changes(start_city, start_route, start_step, end_city, end_route, end_step,
                                         action, map_beliefs)
        if end_route == -1:
            self._arrival(changes, map_beliefs, end_city)
        result.set_result(True)
        result.set_beliefs_to_change(changes)
        return result

    def execute_movement_go_to_step(self, global_workspace, action, map_beliefs) -> ActionExecutionResult:
        """Drive the car from the start step to the action's end step along the route, taking
        ``global_time_to_move`` simulated seconds per step (``move_car_slowly``); when the action ends the
        route, move to the next station and arrive.
        """
        result = ActionExecutionResult()
        pre = action.get_pre_conditions()
        post = action.get_post_conditions()
        start_city = pre[0].get_object_complement()
        end_city = post[0].get_object_complement()
        start_route = pre[1].get_object_complement()
        end_route = post[1].get_object_complement()
        start_step = pre[2].get_object_complement()
        end_step = post[2].get_object_complement()
        minus = -1 if end_route == -1 else 0
        env = map_beliefs.get("BL_Map").get_predicate().get_object_complement()
        correct_start_route = map_beliefs.get("BL_Next_Position_Route").get_predicate().get_object_complement()
        if start_route < 0:
            start_route = correct_start_route
        env.get_route(start_route)
        panel = self.demo.map_panel
        points = panel.ruotes_coords.get(start_route)
        time_to_move = self.global_time_to_move
        while start_step < end_step + minus:
            start_step += 1
            panel.move_car_slowly(points[start_step - 1], time_to_move, start_route, start_step)
        if end_route == -1:
            next_station = TCity.values()[end_city]
            panel.move_car_slowly(panel.stations_coords[next_station], time_to_move, start_route, None)
        changes = self._position_changes(start_city, start_route, start_step, end_city, end_route, end_step,
                                         action, map_beliefs)
        if end_route == -1:
            self._arrival(changes, map_beliefs, end_city)
        result.set_result(True)
        result.set_beliefs_to_change(changes)
        return result

    # ---------------------------------------------------------------- come back desire
    def rise_come_back_desire(self, positions: List[int], map_beliefs) -> ActionExecutionResult:
        """Create the practical desire to come back to the previous city after a danger (saliency 0.9, reward
        0.4, finally interval of 10 hours).
        """
        result = ActionExecutionResult()
        city_position = positions[0]
        bl_come_back = map_beliefs.get("BL_Come_Back_to_City")
        saliency, reward, relax_preference = 0.9, 0.4, 0.4
        bl_current_time = map_beliefs.get("BL_Current_Time")
        finally_start = bl_current_time.get_predicate().get_object_complement()
        finally_end = finally_start + timedelta(hours=10)
        temporal_operator = TemporalOperator()
        temporal_operator.set_type_temporal_operator(TypeTemporalOperator.Finally)
        temporal_operator.set_start_time(finally_start)
        temporal_operator.set_end_time(finally_end)
        formula = TemporalPropositionalFormula()
        formula.set_temporal_operator(temporal_operator)
        formula.set_beliefs([bl_come_back])
        formula.set_formula(bl_come_back.get_name())
        formula.set_list_temporal_propositional_formula_names(None)
        self.practical_desire_number += 1
        come_back = PracticalDesire("Go_Back", formula, None, saliency, reward, relax_preference, [], [],
                                    finally_start, finally_end, None, None, None, None, None, None)
        inh = self.demo.functions_for_belief_inhibition_function
        come_back.set_beliefs_name_for_reasoner(
            list(inh.get_desires_beliefs_functions().reasoner_beliefs_for_come_back(come_back)))
        come_back.set_regions_name_for_reasoner(
            list(inh.get_desires_regions_functions().reasoner_get_regions_for_come_back(map_beliefs)))
        data = PracticalDesireData()
        data.set_practical_desire(come_back)
        data.set_means_end_reasoner_function(
            self.demo.means_end_reasoner_function.reasoner_function_for_come_back_to_city)
        data.add_beliefs_inhibition_functions(
            self.belief_inhibition_functions.get_desires_beliefs_functions().inhibition_beliefs_for_come_back)
        data.add_regions_inhibition_functions(
            self.belief_inhibition_functions.get_desires_regions_functions().inhibition_regions_for_come_back)
        result.set_practical_desires([data])
        bl_come_back.get_predicate().set_object_complement(city_position)      # in place, like Java
        result.set_result(True)
        result.set_beliefs_to_change({"BL_Come_Back_to_City": _me("Object_Complement", city_position)})
        return result

    # ---------------------------------------------------------------- belief bookkeeping
    def update_routes(self, action, map_beliefs) -> Dict[str, Any]:
        """Age the temporary closed routes (Java semantics, including the emulated
        ConcurrentModificationException; see the module docstring).
        """
        changes: Dict[str, Any] = {}
        bl_closed = map_beliefs.get("BL_Temporary_Closed_Routes")
        closed_routes = bl_closed.get_predicate().get_object_complement()
        if closed_routes is None:
            closed_routes = {}
            bl_closed.get_predicate().set_object_complement(closed_routes)
        else:
            changed_routes = False
            outer_removed = False
            for route_number in hashmap_key_order(closed_routes.keys()):
                if outer_removed:
                    raise ConcurrentModificationError("java.util.ConcurrentModificationException")
                changed_route = False
                steps_closed = closed_routes[route_number]
                inner_removed = False
                for step in hashmap_key_order(steps_closed.keys()):
                    if inner_removed:
                        raise ConcurrentModificationError("java.util.ConcurrentModificationException")
                    duration = steps_closed[step] - 1            # local copy: never stored back (Java bug)
                    if duration == 0:
                        changed_route = True
                        changed_routes = True
                        del steps_closed[step]
                        inner_removed = True
                if changed_route:
                    if len(steps_closed) == 0:
                        del closed_routes[route_number]
                        outer_removed = True
                        changes["BL_Route_Status_" + str(route_number)] = _me("Object_Complement", "Green")
                    else:
                        closed_routes[route_number] = steps_closed
            if changed_routes:
                changes["BLT_Temporary_Closed_Routes"] = _me("Object_Complement", closed_routes)
        return changes

    def update_current_time(self, action, map_beliefs) -> Dict[str, Any]:
        current_time = map_beliefs.get("BL_Current_Time").get_predicate().get_object_complement()
        return {"BL_Current_Time": _me("Object_Complement", current_time + timedelta(hours=1))}

    # ---------------------------------------------------------------- remaining actions
    def execute_change_direction(self, global_workspace, action, map_beliefs) -> ActionExecutionResult:
        return ActionExecutionResult()

    def execute_movement_come_back(self, action, map_beliefs) -> ActionExecutionResult:
        return ActionExecutionResult()

    def execute_decision(self, global_workspace, action, map_beliefs) -> ActionExecutionResult:
        """After the danger data: if the car is on a route and the closure would push the current time past the
        maximum satisfaction time of the previous travel, raise the come-back desire (otherwise nothing
        changes; no beliefs are changed).
        """
        result = ActionExecutionResult()
        _ = map_beliefs.get("BL_Danger_on_the_Route")
        bl_dangerous_route = map_beliefs.get("BL_Dangerous_Position_Route")
        _ = map_beliefs.get("BL_Come_Back_to_City")
        _ = map_beliefs.get("BL_Temporary_Closed_Routes")
        bl_closed_duration = map_beliefs.get("BL_Temporary_Closed_Duration")
        _ = bl_dangerous_route.get_predicate().get_object_complement()
        city_position = map_beliefs.get("BL_Position_City").get_predicate().get_object_complement()
        route_position = map_beliefs.get("BL_Position_Route").get_predicate().get_object_complement()
        step_position = map_beliefs.get("BL_Position_Step").get_predicate().get_object_complement()
        duration = bl_closed_duration.get_predicate().get_object_complement()
        changes: Dict[str, Any] = {}
        if route_position > -1:
            max_satisfaction_time = map_beliefs.get(
                "BL_Previous_Travel_Intention_Max_Satisfaction_Time").get_predicate().get_object_complement()
            current_time = map_beliefs.get("BL_Current_Time").get_predicate().get_object_complement()
            new_current_time = current_time + timedelta(hours=duration)
            if new_current_time > max_satisfaction_time:
                go_back = self.rise_come_back_desire([city_position, route_position, step_position], map_beliefs)
                changes.update(go_back.get_beliefs_to_change())          # computed but never used (Java)
                result.set_practical_desires(go_back.get_practical_desires())
        result.set_result(True)
        return result

    def execute_refuelling(self, global_workspace, action, map_beliefs) -> ActionExecutionResult:
        """Refuel in the nearest town: reset the fuel level and the position beliefs."""
        cf = self.common_functions
        result = ActionExecutionResult()
        cf.print("I've reached the nearest town!\nNow I'm going to get fuel!")
        cf.print("Now, I'm refueling")
        bl_warning = map_beliefs.get("BL_Low_Fuel_Level_Warning")
        fuel_level = action.get_params()[0]
        position_city_number = action.get_params()[1]
        result.set_beliefs_to_change({
            "BL_Fuel_Level": ["Object_Complement", fuel_level],
            "BL_Refuel_to_City": ["Object_Complement", bl_warning],
            "BL_Position_City": ["Object_Complement", position_city_number],
            "BL_Position_Route": ["Object_Complement", -1],
            "BL_Position_Step": ["Object_Complement", 0],
        })
        cf.print("I refueled!")
        cf.print("Now I continue to fulfill my desires, if there are any")
        result.set_result(True)
        return result

    def execute_declare_the_refuel(self, global_workspace, action, map_beliefs) -> ActionExecutionResult:
        """Announce the low fuel and set the next position city to the refuelling town."""
        result = ActionExecutionResult()
        city_number = action.get_params()[0]
        city_to_refuel = TCity.values()[city_number].name
        self.contatore += 1
        self.common_functions.print_colored_text(
            "My fuel is low! I need to refuel.\nI go in " + city_to_refuel + " to refuel!", 2)
        for name in ("BL_Next_Position_City", "BL_Position_City", "BL_Position_Step", "BL_Position_Route",
                     "BL_Next_Position_Route", "BL_Next_Position_Step"):
            _ = map_beliefs.get(name).get_predicate().get_object_complement()
        result.set_result(True)
        result.set_beliefs_to_change({"BL_Next_Position_City": ["Object_Complement", city_number]})
        return result
