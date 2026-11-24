"""Executive Perception Function.

Java: TExecutive_Perception_Function, TPerceptions_Processing, TInformation_Extraction,
TStimulus_Filtering.

Pipeline, once per loop of the thread: sensors -> perceptions -> (information extraction function
of the sensor) stimuli -> (saliency map + manipulation function) -> filtered stimuli -> Global
Workspace ``set_filtered_stimuli``.

Java behaviour kept on purpose (README, quirks):
* ``PerceptionsProcessing.execute`` clears the acquired perceptions before polling the sensors,
  so perceptions pushed with ``insert_perception`` are lost at the next loop. Only the sensor
  functions registered with ``register_perception_function`` produce perceptions.
* ``register_perception_function`` ignores sensors not added with ``add_sensor``.
* ``StimulusFiltering.execute`` compares the saliency with the saliency threshold only when there
  are inhibited regions, otherwise with the attention threshold (on the ORIGINAL stimulus).
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from .agent_thread import AgentBaseThread
from .enums import TypeUpdateContract as C
from .handlers import (InformationExtractionFunctionHandler, PerceptionProcessingSensorFunctionHandler,
                       StimulusFilteringManipulateStimulusFunctionHandler)
from .maps import MapBeliefToSalienceStimuli
from .model import Perception
from .protected import BooleanProtectedObject, ProtectedList


class PerceptionsProcessing:
    """Polls the registered sensors and stores the perceptions (see the module docstring for the Java quirk on
    the buffer).
    """
    def __init__(self, owner: Any):
        self.parent = owner
        self.acquired_perceptions: ProtectedList = ProtectedList()
        self._lock = threading.RLock()
        self.sensors: Dict[str, None] = {}
        self.sensor_function_handler = PerceptionProcessingSensorFunctionHandler()
        self.has_new_perceptions_flag = BooleanProtectedObject(False)

    def insert_perception(self, time, data: Optional[List[Any]], source: str) -> None:
        with self._lock:
            if data is not None:
                self.acquired_perceptions.add(Perception(time, data, source))
                self.has_new_perceptions_flag.set_true()

    def insert_perceptions(self, time, data_matrix: Optional[List[List[Any]]], source: str) -> None:
        with self._lock:
            if data_matrix:
                self.acquired_perceptions.add_all([Perception(time, d, source) for d in data_matrix])
                self.has_new_perceptions_flag.set_true()

    def get_last_acquired_perceptions(self) -> List[Perception]:
        with self._lock:
            self.has_new_perceptions_flag.set_false()
            return self.acquired_perceptions.read_and_clear()

    def execute(self) -> None:
        self.acquired_perceptions.clear()
        for sensor in list(self.sensors):
            self.acquired_perceptions.add_all(self.sensor_function_handler.execute_function_for_sensor(sensor))

    def add_sensor(self, sensor: str) -> None:
        self.sensors[sensor] = None

    def add_sensors(self, sensors: List[str]) -> None:
        for s in sensors:
            self.sensors[s] = None

    def remove_sensor_by_object(self, sensor: str) -> None:
        self.sensors.pop(sensor, None)
        self.sensor_function_handler.unregister_function(sensor)

    def has_new_perceptions(self) -> bool:
        return bool(self.has_new_perceptions_flag.read())

    def register_perception_function(self, sensor: str, func: Callable) -> None:
        if sensor in self.sensors:
            self.sensor_function_handler.register_function(sensor, func)

    def unregister_perception_function(self, sensor: str) -> bool:
        if sensor in self.sensors:
            return self.sensor_function_handler.unregister_function(sensor)
        return False


class InformationExtraction:
    """Turns perceptions into stimuli through the extraction function registered for each sensor."""
    def __init__(self, owner: Any):
        self.parent = owner
        self.handler = InformationExtractionFunctionHandler()
        self.last_generated_stimuli: ProtectedList = ProtectedList()

    def execute(self, new_perceptions: List[Perception], map_beliefs: Dict[str, Any],
                map_regions: Dict[str, Any]) -> None:
        self.last_generated_stimuli.clear()
        for perception in new_perceptions:
            self.last_generated_stimuli.add_all(
                self.handler.execute_function_for_raw_data(
                    perception.get_source(), perception, map_beliefs, map_regions))

    def get_last_stimuli(self) -> List[Any]:
        return self.last_generated_stimuli.read_and_clear()

    def register_information_extraction_function(self, sensor: str, func: Callable) -> None:
        self.handler.register_function(sensor, func)

    def unregister_information_extraction_function(self, sensor: str) -> bool:
        return self.handler.unregister_function(sensor)


class StimulusFiltering:
    """Assigns saliencies to stimuli, applies the manipulation functions and keeps those above the threshold.
    """
    def __init__(self, owner: Any):
        self.owner = owner
        self.inhibited_beliefs: List[Any] = []
        self.inhibited_regions: List[Any] = []
        self.map_stimuli_to_salience = MapBeliefToSalienceStimuli()
        self.map_stimuli_to_salience_path = ""
        self.survived_stimuli: List[Any] = []
        self.manipulate_stimulus_function_handler = StimulusFilteringManipulateStimulusFunctionHandler()

    def execute(self, new_stimuli: List[Any], saliency_threshold: float, attention_threshold: float,
                inhibited_regions: List[Any], inhibited_beliefs: List[Any]) -> None:
        """Filter ``new_stimuli``: with inhibited regions compare the manipulated stimulus' saliency with the
        saliency threshold, otherwise the original stimulus' saliency with the attention threshold (Java
        behaviour).
        """
        temp_survived: List[Any] = []
        self.survived_stimuli.clear()
        relevant = self.apply_filter(new_stimuli, inhibited_regions)
        for index, relevant_stimulus in enumerate(relevant):
            if len(inhibited_regions) > 0 and relevant_stimulus is not None:
                if relevant_stimulus.get_saliency() > saliency_threshold:
                    temp_survived.append(relevant_stimulus)
            else:
                stimulus = new_stimuli[index]
                if stimulus.get_saliency() > attention_threshold:
                    temp_survived.append(relevant_stimulus)
        if len(temp_survived) > 0:
            self.survived_stimuli.extend(temp_survived)

    def apply_filter(self, new_stimuli: List[Any], inhibited_regions: List[Any]) -> List[Any]:
        """Assign the saliency mapped to each stimulus type, then run the manipulation function registered for the type; returns one stimulus per input.
        """
        survived: List[Any] = []
        mapped = self.map_stimuli_to_salience.get_mapped_stimuli()
        for stimulus in new_stimuli:
            relevant = None
            type_stimulus = stimulus.get_type_belief()
            if type_stimulus in mapped:
                relevant = stimulus
                relevant.update_saliency(mapped[type_stimulus])
            if relevant is None:
                relevant = stimulus
            relevant = self.manipulate_stimulus_function_handler.execute_function_for_stimulus(
                relevant, inhibited_regions)
            survived.append(relevant)
        return survived

    def load_saliencies_for_stimuli(self, filename: str) -> None:
        self.map_stimuli_to_salience_path = filename
        self.map_stimuli_to_salience.load_mapped_epistemic_desires(self.map_stimuli_to_salience_path)

    def register_function(self, stimulus_type: str, func: Callable) -> None:
        self.manipulate_stimulus_function_handler.register_function(stimulus_type, func)

    def unregister_function(self, stimulus_type: str) -> bool:
        return self.manipulate_stimulus_function_handler.unregister_function(stimulus_type)

    def add_saliency_to_map_stimulus_to_saliency(self, stimulus_type: str, saliency: float) -> None:
        self.map_stimuli_to_salience.add_type_belief_to_salience_stimuli(stimulus_type, saliency)

    def get_survived_stimuli(self) -> List[Any]:
        result = list(self.survived_stimuli)
        self.survived_stimuli.clear()
        return result


class ExecutivePerceptionFunction(AgentBaseThread):
    """Executive Perception thread: sensors -> perceptions -> stimuli -> filtered stimuli -> Global Workspace.
    """
    def __init__(self, agent: Any):
        super().__init__(agent, "Executive Perception Function")
        self.global_workspace = agent.get_global_workspace()
        self.sensors: Dict[Any, None] = {}
        self.perceptions_processing = PerceptionsProcessing(self)
        self.information_extraction = InformationExtraction(self)
        self.stimulus_filtering = StimulusFiltering(self)
        self.perceptions: List[Perception] = []
        self.stimuli: List[Any] = []
        self.filtered_stimuli: List[Any] = []
        self.inhibited_beliefs: List[Any] = []
        self.inhibited_regions: List[Any] = []
        self.uninhibited_beliefs: List[Any] = []
        self.uninhibited_regions: List[Any] = []
        self.map_uninhibited_beliefs: Dict[str, Any] = {}
        self.map_uninhibited_regions: Dict[str, Any] = {}
        self.saliency_threshold = 0.0
        self.attention_threshold = 0.0
        thresholds = self.global_workspace.get_saliency_and_attention_thresholds()
        if thresholds is not None:
            self.saliency_threshold = thresholds.get_object_first()
            self.attention_threshold = thresholds.get_object_second()

    def insert_in_list_update_contract(self) -> None:
        gw = self.agent.get_global_workspace()
        gw.insert_for_update_contract(C.Updated_Perceptions, self)
        gw.insert_for_update_contract(C.Updated_Thresholds, self)
        gw.insert_for_update_contract(C.Updated_Uninhibited_Data, self)

    def execute(self) -> None:
        """One loop: refresh thresholds and uninhibited data when notified, poll the sensors, extract stimuli, filter them and publish the survivors to the Global Workspace.
        """
        mh = self.message_handler
        gw = self.global_workspace
        if mh.read_value_and_clear("thresholds"):
            thresholds = gw.get_saliency_and_attention_thresholds()
            self.saliency_threshold = thresholds.get_object_first()
            self.attention_threshold = thresholds.get_object_second()
        if mh.read_value_and_clear("uninhibited_data"):
            self.inhibited_beliefs = list(gw.get_inhibited_beliefs_from_mm())
            self.inhibited_regions = list(gw.get_inhibited_regions_from_mm())
            self.uninhibited_beliefs = [b for b in gw.get_all_beliefs_from_mm()
                                        if b not in self.inhibited_beliefs]
            self.map_uninhibited_beliefs = dict(gw.get_map_uninhibited_beliefs())
            self.map_uninhibited_regions = dict(gw.get_map_uninhibited_regions())
            self.uninhibited_regions = [r for r in gw.get_all_regions_from_mm()
                                        if r not in self.inhibited_regions]
        self.perceptions = []
        self.stimuli = []
        self.filtered_stimuli = []
        self.perceptions_processing.execute()
        self.perceptions.extend(self.perceptions_processing.get_last_acquired_perceptions())
        if len(self.perceptions) > 0:
            self.information_extraction.execute(self.perceptions, self.map_uninhibited_beliefs,
                                                self.map_uninhibited_regions)
            self.stimuli.extend(self.information_extraction.get_last_stimuli())
            if len(self.stimuli) > 0:
                self.stimulus_filtering.execute(self.stimuli, self.saliency_threshold,
                                                self.attention_threshold, self.inhibited_regions,
                                                self.inhibited_beliefs)
                self.filtered_stimuli.extend(self.stimulus_filtering.get_survived_stimuli())
            if len(self.filtered_stimuli) > 0:
                gw.set_filtered_stimuli(self.filtered_stimuli)

    # ---- registration API (Java names)
    def register_perception_function(self, sensor: str, func: Callable) -> None:
        self.perceptions_processing.register_perception_function(sensor, func)

    def unregister_perception_function(self, sensor: str) -> bool:
        return self.perceptions_processing.unregister_perception_function(sensor)

    def add_sensor(self, sensor: str) -> None:
        self.sensors[sensor] = None
        self.perceptions_processing.add_sensor(sensor)

    def add_sensors(self, sensors: List[str]) -> None:
        for s in sensors:
            self.sensors[s] = None
        self.perceptions_processing.add_sensors(sensors)

    def remove_sensor_by_object(self, sensor: str) -> None:
        self.sensors.pop(sensor, None)
        self.perceptions_processing.remove_sensor_by_object(sensor)
        if sensor is not None:
            self.unregister_information_extraction_function(sensor)

    def register_information_extraction_function(self, sensor: str, func: Callable) -> None:
        self.information_extraction.register_information_extraction_function(sensor, func)

    def unregister_information_extraction_function(self, sensor: str) -> bool:
        return self.information_extraction.unregister_information_extraction_function(sensor)

    def get_sensors(self) -> List[Any]:
        return list(self.sensors)

    def load_saliencies_for_stimuli(self, filename: str) -> None:
        self.stimulus_filtering.load_saliencies_for_stimuli(filename)

    def register_stimulus_filtering_function(self, stimulus_type: str, func: Callable) -> None:
        self.stimulus_filtering.register_function(stimulus_type, func)

    def unregister_stimulus_filtering_function(self, stimulus_type: str) -> bool:
        return self.stimulus_filtering.unregister_function(stimulus_type)
