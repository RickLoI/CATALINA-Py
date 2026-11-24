"""Wiring of the case study (Java: Autonomous_Vehicle_Demo).

``AutonomousVehicleDemo.start()`` follows Java ``Start()`` step by step: build the agent from the
``Data`` folder, create the map and one region per route, register every function group on the
agent, then suspend the seven executives. ``start_av()`` is the "Start AVA" button.

Differences from Java (the GUI is gone, the agent is the same):
* the output of the agent goes to ``event_log`` (see ``events``) instead of ``Log_Memo``;
* every wait goes through ``clock`` (``SimClock`` by default, speed adjustable);
* the two stimulus buttons are ``send_a_danger()`` / ``send_low_fuel_signal()`` (scenarios call them);
* the answers to the traffic-control questions can be scripted (``scripted_answers``).
"""
from __future__ import annotations

import os
import threading
from typing import Any, Iterable, List, Optional

from catalina.agent import Agent
from catalina.clock import SimClock

from .common import CommonFunctions
from .environment import Environment, RegionSimulation, create_map
from .events import EventLog
from .functions_desires import FunctionsForExogenousDesirePromotion
from .functions_execution import FunctionsForOptionExecution
from .functions_inhibition import FunctionsForInhibitionFunction, FunctionsForRegionInhibitionFunction
from .functions_perception import (FunctionsForGWMemoryMaintenanceUpdateBeliefFunction,
                                   FunctionsForInformationExtraction, FunctionsForPerceptionProcessing,
                                   FunctionsForStimulusFiltering)
from .functions_reasoner import (FunctionsForDeliberationProcess, FunctionsForFilteringDesiresFunction,
                                 FunctionsForMeansEndReasoner)
from .map_panel import MapPanelModel

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(HERE, "Data")
CAR_IMAGE = os.path.join(HERE, "img", "auto.png")


class AutonomousVehicleDemo:
    """The case study wired together (Java: Autonomous_Vehicle_Demo). Create it, call ``start()`` (build agent,
    map and functions), then ``start_av()``; stop with ``end_simulation()``.
    """
    def __init__(self, data_dir: Optional[str] = None, clock: Optional[Any] = None,
                 scripted_answers: Optional[Iterable[str]] = None, echo: bool = False):
        self.data_directory = data_dir or DEFAULT_DATA_DIR
        self.clock = clock if clock is not None else SimClock(1.0)
        self.scripted_answers: List[str] = list(scripted_answers or [])
        self.stopping = threading.Event()
        self.event_log = EventLog(self.clock, echo=echo)
        self.common_functions = CommonFunctions(self)
        self.agent: Optional[Agent] = None
        self.map: Optional[Environment] = None
        self.map_panel: Optional[MapPanelModel] = None
        self.long_memory = None
        self.functions_for_belief_inhibition_function: Optional[FunctionsForInhibitionFunction] = None
        self.functions_for_region_inhibition_function: Optional[FunctionsForRegionInhibitionFunction] = None
        self.functions_for_plan_execution: Optional[FunctionsForOptionExecution] = None
        self.perception_processing_functions: Optional[FunctionsForPerceptionProcessing] = None
        self.means_end_reasoner_function: Optional[FunctionsForMeansEndReasoner] = None

    # ------------------------------------------------------------------ Java Start()
    def start(self) -> "AutonomousVehicleDemo":
        """Java ``Start()``: map panel, agent, map and regions, then register every function group on the
        executives in the Java order, and suspend the seven executives until ``start_av()``.
        """
        self.map_panel = MapPanelModel(self, CAR_IMAGE)
        self.common_functions.print_colored_text("Autonomous Vehicle Agent Simulation", 2)
        self.agent = agent = Agent(self.data_directory, clock=self.clock)
        attention_modulation = agent.get_attention_modulation_component()
        desire_handler = agent.get_desire_handler_component()
        memory_maintenance = agent.get_executive_memory_maintenance_function()
        perception = agent.get_executive_perception_function()
        inhibition = agent.get_executive_inhibition_function()
        switching = agent.get_executive_switching_function()
        action_control = agent.get_action_control()
        reasoner = agent.get_executive_reasoner_function()
        self.long_memory = agent.get_long_memory()
        self.initialize_data_simulation()

        self.perception_processing_functions = FunctionsForPerceptionProcessing(self)
        self.perception_processing_functions.add_function_to_perception_processing(perception)
        FunctionsForInformationExtraction(self).add_function_to_information_extraction(perception)
        FunctionsForStimulusFiltering(self).add_function_to_stimulus_filtering(perception)
        FunctionsForGWMemoryMaintenanceUpdateBeliefFunction(self).add_function_to_gw_memory_maintenance_function(
            memory_maintenance)

        self.functions_for_belief_inhibition_function = FunctionsForInhibitionFunction(self)
        self.functions_for_belief_inhibition_function.set_inhibition_function(inhibition)
        self.functions_for_belief_inhibition_function.add_inhibition_functions()
        self.functions_for_region_inhibition_function = FunctionsForRegionInhibitionFunction(self)
        self.functions_for_region_inhibition_function.set_inhibition_function(inhibition)
        self.functions_for_region_inhibition_function.add_inhibition_functions()

        FunctionsForExogenousDesirePromotion(self).add_functions_to_exogenous_desire_promotion(desire_handler)
        self.means_end_reasoner_function = FunctionsForMeansEndReasoner(self)
        self.means_end_reasoner_function.add_functions_to_means_end_reasoner(reasoner)
        self.means_end_reasoner_function.add_beliefs_to_means_end_reasoner(reasoner)
        FunctionsForFilteringDesiresFunction(self).add_function_to_filter_process(reasoner)
        FunctionsForDeliberationProcess(self).add_function_to_means_end_reasoner(reasoner)
        self.functions_for_plan_execution = FunctionsForOptionExecution(self)
        self.functions_for_plan_execution.add_function_to_switching_function(action_control)

        for executive in (desire_handler, attention_modulation, inhibition, perception, memory_maintenance,
                          reasoner, switching):
            executive.suspend()
        return self

    def initialize_data_simulation(self) -> None:
        self.map = Environment()
        create_map(self.map)
        for route in self.map.all_routes:                       # Initialize_Region_Simulation
            self.long_memory.add_region(RegionSimulation(route))
        bl_map = self.long_memory.get_all_map_beliefs().get("BL_Map")
        bl_map.get_predicate().set_object_complement(self.map)

    # ------------------------------------------------------------------ buttons
    def start_av(self) -> None:
        self.map_panel.start_av()

    def suspend_av(self) -> None:
        self.map_panel.suspend_av()

    def resume_av(self) -> None:
        self.map_panel.resume_av()

    def send_a_danger(self) -> None:
        self.event_log.emit("stimulus", name="danger")
        self.perception_processing_functions.send_a_danger()

    def send_low_fuel_signal(self) -> None:
        self.event_log.emit("stimulus", name="low_fuel")
        self.perception_processing_functions.send_low_fuel_signal()

    def submit_tcs_response(self, text: str) -> None:
        """GUI text field + 'Send' button."""
        self.perception_processing_functions.virtual_tcs.submit_response(text)

    # ------------------------------------------------------------------ end
    def end_simulation(self, join_timeout: float = 5.0) -> None:
        """Stops every thread (Java ``End_Simulation`` calls ``System.exit``)."""
        self.stopping.set()
        if self.agent is not None:
            self.agent.stop_executives()
        self.clock.stop()
        if self.agent is not None:
            for thread in self.agent.all_threads():
                if thread.is_alive():
                    thread.join(join_timeout)
        self.common_functions.print("End Simulation.")

    # ------------------------------------------------------------------ state helpers
    def belief_value(self, name: str) -> Any:
        belief = self.long_memory.get_all_map_beliefs().get(name)
        return None if belief is None else belief.get_predicate().get_object_complement()
