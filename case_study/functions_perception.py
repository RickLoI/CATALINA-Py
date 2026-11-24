"""Perception side of the case study.

Java: TFunctions_for_Perception_Processing, TFunctions_for_Information_Extraction,
TFunctions_for_Stimulus_Filtering, TFunctions_for_GW_Memory_Maintenance_Update_Belief_Function.

Java behaviour kept on purpose:
* ``See_Road_in_Front`` calls ``Reset_Sensor`` and then sets the camera as unavailable, so the
  camera works only once per run: a second 'danger' signal is never seen.
* The sensor ``GPS`` is registered with the perception function but never added as a sensor
  (``Get_Current_Position_from_GPS`` is dead code).
* ``Update_Normal_Belief_from_BLTS_Stimulus_Low_Fuel`` stores a *Belief object* (the warning
  belief) as value of ``BL_Low_Fuel_Level``.
* In ``Update_Normal_Beliefs_from_Danger_Data_from_TCS`` the second ``BL_Danger_on_the_Route``
  entry replaces the first.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from catalina.model import Perception

from .domain import TTypeDanger


class FunctionsForPerceptionProcessing:
    """Sensors of the case study (front camera, traffic control service, fuel sensor), their availability flags
    and the two stimulus buttons (``send_a_danger``, ``send_low_fuel_signal``).
    """
    def __init__(self, demo: Any):
        from .traffic_control import TrafficControlService, VirtualGPS
        self.demo = demo
        self.common_functions = demo.common_functions
        self.sensors: List[str] = ["Front_Virtual_Camera", "Traffic_Control_Service", "Fuel_Sensor"]
        self.sensors_avaible: Dict[str, bool] = {"Front_Virtual_Camera": True, "Traffic_Control_Service": True,
                                                 "Fuel_Sensor": True}
        self.see_a_danger = False
        self.low_fuel_signal = False
        self.virtual_gps = VirtualGPS(demo.agent)
        self.virtual_tcs = TrafficControlService(demo, scripted_answers=demo.scripted_answers)

    def add_sensor_to_perception_processing(self, executive_perception) -> None:
        executive_perception.add_sensors(list(self.sensors))

    def get_current_position_from_gps(self, sensor: str) -> List[Perception]:
        perceptions: List[Perception] = []
        data: List[Any] = list(self.virtual_gps.get_current_position())
        if len(data) > 0:
            data.append("Correct_Movement!")
            perceptions.append(Perception(datetime.now(), data, sensor))
        return perceptions

    def see_road_in_front(self, sensor: str) -> List[Perception]:
        """Front camera: if a danger was signalled and the camera is available, produce one 'Danger on the
        route!' perception and make the camera unavailable (works once per run, as in Java).
        """
        perceptions: List[Perception] = []
        can_capture = self.sensors_avaible.get("Front_Virtual_Camera")
        if can_capture:
            if self.see_a_danger:
                self.see_a_danger = False
                self.reset_sensor("Front_Virtual_Camera")
                perceptions.append(Perception(datetime.now(), ["Danger on the route!"], sensor))
                self.sensors_avaible["Front_Virtual_Camera"] = False
        return perceptions

    def get_low_fuel_signal(self, sensor: str) -> List[Perception]:
        perceptions: List[Perception] = []
        if self.low_fuel_signal:
            self.low_fuel_signal = False
            low_fuel = 24          # simulated fuel level, range 0..100
            perceptions.append(Perception(datetime.now(), [low_fuel], sensor))
        return perceptions

    def get_danger_data_from_tcs(self, sensor: str) -> List[Perception]:
        perceptions: List[Perception] = []
        data: List[Any] = list(self.virtual_tcs.get_danger_data())
        if len(data) > 0:
            data.insert(0, "Danger_Data_Acquired!")
            perceptions.append(Perception(datetime.now(), data, sensor))
        return perceptions

    def add_function_to_perception_processing(self, executive_perception) -> None:
        self.add_sensor_to_perception_processing(executive_perception)
        executive_perception.register_perception_function("Front_Virtual_Camera", self.see_road_in_front)
        executive_perception.register_perception_function("GPS", self.get_current_position_from_gps)
        executive_perception.register_perception_function("Traffic_Control_Service", self.get_danger_data_from_tcs)
        executive_perception.register_perception_function("Fuel_Sensor", self.get_low_fuel_signal)

    def reset_sensor(self, sensor_name: str) -> None:
        self.sensors_avaible[sensor_name] = True

    # ---- the two stimulus buttons
    def send_a_danger(self) -> None:
        self.see_a_danger = True

    def send_low_fuel_signal(self) -> None:
        self.low_fuel_signal = True


class FunctionsForInformationExtraction:
    """Information extraction: turn the perceptions of each sensor into the case-study stimuli."""
    def __init__(self, demo: Any):
        self.demo = demo
        self.common_functions = demo.common_functions

    def manage_positions_acquired(self, perception, map_uninhibited_beliefs, map_uninhibited_regions) -> List[Any]:
        return []

    def manage_stimulus_danger_on_the_route(self, perception, map_uninhibited_beliefs,
                                            map_uninhibited_regions) -> List[Any]:
        """Perception -> danger stimulus, carrying the car position (route, step, city) for the traffic control
        query.
        """
        cf = self.common_functions
        stimuli: List[Any] = []
        stimulus = map_uninhibited_beliefs.get("ST_Stimulus_Danger_on_the_Route")
        belief_route = map_uninhibited_beliefs.get("BL_Position_Route")
        route_position = -1
        if belief_route is not None:
            route_position = int(belief_route.get_predicate().get_object_complement())
        else:
            cf.print_colored_text("An Error occours in 'Manage_Stimulus_Danger_on_the_Route' when AV gets "
                                  "the BLT_Position_Route.", 2)
        belief_step = map_uninhibited_beliefs.get("BL_Position_Step")
        step_position = -1
        if belief_step is not None:
            step_position = int(belief_step.get_predicate().get_object_complement())
        else:
            cf.print_colored_text("An Error occours in 'Manage_Stimulus_Danger_on_the_Route' when AV gets "
                                  "the BLT_Position_Step.", 2)
        belief_city = map_uninhibited_beliefs.get("BL_Position_City")
        city_position = -1
        if belief_city is not None:
            city_position = int(belief_city.get_predicate().get_object_complement())
        else:
            cf.print_colored_text("An Error occours in 'Manage_Stimulus_Danger_on_the_Route' when AV gets "
                                  "the BLT_Position_City.", 2)
        if stimulus is not None:
            stimulus.get_predicate().set_subject([city_position, route_position, step_position])
            stimuli.append(stimulus)
        else:
            cf.print_colored_text("An Error occours in 'Manage_Stimulus_Danger_on_the_Route' when AV gets "
                                  "the Stimulus.", 2)
        return stimuli

    def manage_stimulus_danger_data_acquired(self, perception, map_uninhibited_beliefs,
                                             map_uninhibited_regions) -> List[Any]:
        """Perception of the traffic-control data -> 'Danger data from TCS' stimulus."""
        stimuli: List[Any] = []
        stimulus = map_uninhibited_beliefs.get("ST_Stimulus_Danger_Data_from_TCS")
        # Danger_Data: 0 Information, 1 City, 2 Route, 3 Step, 4 Dangerous route, 5 Type ordinal, 6 Duration
        if stimulus is not None:
            predicate = stimulus.get_predicate()
            predicate.set_subject(perception.get_perceived_data()[0])
            predicate.set_object_complement(perception)
            stimuli.append(stimulus)
        else:
            self.common_functions.print_colored_text(
                "An Error occours in 'Manage_Stimulus_Danger_on_the_Route' when AV gets the Stimulus.", 2)
        return stimuli

    def mangage_low_fuel_level_signal(self, perception, map_uninhibited_beliefs,
                                      map_uninhibited_regions) -> List[Any]:
        """Low-fuel perception -> low-fuel stimulus."""
        stimuli: List[Any] = []
        stimulus = map_uninhibited_beliefs.get("ST_Stimulus_Low_Fuel")
        if stimulus is not None:
            stimuli.append(stimulus)
        else:
            self.common_functions.print_colored_text(
                "An Error occours in 'Mangage_Low_Fuel_Level_Signal' when AV gets the Stimulus.", 2)
        return stimuli

    def add_function_to_information_extraction(self, executive_perception) -> None:
        executive_perception.register_information_extraction_function(
            "Front_Virtual_Camera", self.manage_stimulus_danger_on_the_route)
        executive_perception.register_information_extraction_function(
            "Traffic_Control_Service", self.manage_stimulus_danger_data_acquired)
        executive_perception.register_information_extraction_function(
            "Fuel_Sensor", self.mangage_low_fuel_level_signal)


class FunctionsForStimulusFiltering:
    """Stimulus filters: set the saliency of each stimulus type (danger 0.9, danger data from the traffic
    control 0.92, low fuel 0.9).
    """
    def __init__(self, demo: Any):
        self.demo = demo
        self.common_functions = demo.common_functions

    def check_danger_on_the_road(self, stimulus, regions):
        stimulus.update_saliency(0.9)
        return stimulus

    def check_danger_data_from_tcs(self, stimulus, regions):
        stimulus.update_saliency(0.92)
        return stimulus

    def check_low_fuel_level_warning(self, stimulus, regions):
        stimulus.update_saliency(0.9)
        return stimulus

    def add_function_to_stimulus_filtering(self, executive_perception) -> None:
        executive_perception.load_saliencies_for_stimuli(self.demo.data_directory)
        executive_perception.register_stimulus_filtering_function(
            "BLTS_Stimulus_Danger_on_the_Route", self.check_danger_on_the_road)
        executive_perception.register_stimulus_filtering_function(
            "BLTS_Stimulus_Danger_Data_from_TCS", self.check_danger_data_from_tcs)
        executive_perception.register_stimulus_filtering_function(
            "BLTS_Stimulus_Low_Fuel", self.check_low_fuel_level_warning)


class FunctionsForGWMemoryMaintenanceUpdateBeliefFunction:
    """Belief updates triggered by each stimulus type when it enters the Global Workspace."""
    def __init__(self, demo: Any):
        self.demo = demo
        self.common_functions = demo.common_functions

    @staticmethod
    def _result():
        from catalina.memory_maintenance import UpdateBeliefFunctionResult
        return UpdateBeliefFunctionResult()

    def update_normal_belief_from_blts_stimulus_danger_on_the_route(self, stimulus, map_beliefs, recall_belief):
        """Danger stimulus -> mark the route 'Under_maintenance' and record the position of the danger."""
        result = self._result()
        bl_position_route = map_beliefs.get("BL_Position_Route")
        route_number = bl_position_route.get_predicate().get_object_complement()
        belief_name = "BL_Route_Status_" + str(route_number)
        bl_route_status = map_beliefs.get(belief_name)
        if bl_route_status is None:
            bl_next_position_route = map_beliefs.get("BL_Next_Position_Route")
            route_number = bl_next_position_route.get_predicate().get_object_complement()
            belief_name = "BL_Route_Status_" + str(route_number)
            bl_route_status = map_beliefs.get(belief_name)
        bl_route_status.get_predicate().set_object_complement("Under_maintenance")
        bl_position_city = map_beliefs.get("BL_Position_City")
        bl_position_step = map_beliefs.get("BL_Position_Step")
        city_number = bl_position_city.get_predicate().get_object_complement()
        step_number = bl_position_step.get_predicate().get_object_complement()
        st_danger = map_beliefs.get("ST_Stimulus_Danger_on_the_Route")
        st_danger.get_predicate().set_subject([city_number, route_number, step_number])
        result.set_result(True)
        return result

    def update_normal_beliefs_from_danger_data_from_tcs(self, stimulus, map_beliefs, recall_belief):
        """TCS data stimulus -> update the danger, closed-route status, come-back city, current time and
        temporary closure beliefs.
        """
        result = self._result()
        predicate = stimulus.get_predicate()
        # Danger_Data: 0 Information, 1 City, 2 Route, 3 Step, 4 Dangerous route, 5 Type ordinal, 6 Duration
        perception = predicate.get_object_complement()
        data = perception.get_perceived_data()
        city_position = data[1]
        step_position = data[3]
        dangerous_route = data[4]
        duration = data[6]
        names = ["BL_Danger_on_the_Route", "BL_Route_Status_" + str(dangerous_route), "BL_Dangerous_Position_Route",
                 "BL_Come_Back_to_City", "BL_Current_Time", "BL_Temporary_Closed_Routes",
                 "BL_Temporary_Closed_Duration"]
        recalled: Dict[str, Any] = {}
        recalled.update(recall_belief(names))
        recalled.update(map_beliefs)
        type_danger = TTypeDanger.values()[data[5]]
        changes: Dict[str, Any] = {}
        changes["BL_Danger_on_the_Route"] = ["Subject", dangerous_route, "Me"]
        changes["BL_Danger_on_the_Route"] = ["Object_Complement", type_danger, "Me"]
        changes["BL_Route_Status_" + str(dangerous_route)] = ["Object_Complement", "Under_maintenance", "Me"]
        changes["BL_Dangerous_Position_Route"] = ["Object_Complement", dangerous_route, "Me"]
        changes["BL_Come_Back_to_City"] = ["Object_Complement", city_position, "Me"]
        changes["BL_Temporary_Closed_Duration"] = ["Object_Complement", duration, "Me"]
        bl_closed = recalled.get("BL_Temporary_Closed_Routes")
        if bl_closed.get_predicate().get_object_complement() is None:
            closed_routes = {dangerous_route: {step_position: duration}}
        else:
            closed_routes = bl_closed.get_predicate().get_object_complement()
            steps_closed = closed_routes.get(dangerous_route)
            if steps_closed is None:
                steps_closed = {}
            steps_closed[step_position] = duration
            closed_routes[dangerous_route] = steps_closed
        changes["BL_Temporary_Closed_Routes"] = ["Object_Complement", closed_routes, "Me"]
        belief_route_status = recalled.get("BL_Temporary_Closed_Routes")
        if belief_route_status is not None:
            map_closed = belief_route_status.get_predicate().get_object_complement()
            if map_closed is None:
                map_closed = {}
            list_steps = map_closed.get(dangerous_route)
            if list_steps is None:
                list_steps = {}
            list_steps[step_position] = duration
            map_closed[dangerous_route] = list_steps
            changes["BL_Temporary_Closed_Routes"] = ["Object_Complement", map_closed]
        else:
            self.common_functions.print_colored_text("The BL_Danger_on_the_Route is not Uninhibited!", 2)
        result.set_beliefs_to_change(changes)
        result.set_result(True)
        return result

    def update_normal_belief_from_blts_stimulus_low_fuel(self, stimulus, map_beliefs, recall_belief):
        """Low-fuel stimulus -> set the fuel level and low-fuel belief from the warning."""
        result = self._result()
        bl_low_fuel_level_warning = map_beliefs.get("BL_Low_Fuel_Level_Warning")
        current_fuel_level = bl_low_fuel_level_warning.get_predicate().get_object_complement()
        changes: Dict[str, Any] = {
            "BL_Fuel_Level": ["Object_Complement", current_fuel_level, "Me"],
            "BL_Low_Fuel_Level": ["Object_Complement", bl_low_fuel_level_warning, "Me"],
        }
        result.set_beliefs_to_change(changes)
        result.set_result(True)
        return result

    def add_function_to_gw_memory_maintenance_function(self, executive_memory) -> None:
        executive_memory.register_update_beliefs_function(
            "BLTS_Stimulus_Danger_on_the_Route", self.update_normal_belief_from_blts_stimulus_danger_on_the_route)
        executive_memory.register_update_beliefs_function(
            "BLTS_Stimulus_Danger_Data_from_TCS", self.update_normal_beliefs_from_danger_data_from_tcs)
        executive_memory.register_update_beliefs_function(
            "BLTS_Stimulus_Low_Fuel", self.update_normal_belief_from_blts_stimulus_low_fuel)
