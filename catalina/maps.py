"""Stimulus/belief maps loaded from XML or registered by code.

Java: TMapped_Epistemic_Desire, TMap_Stimulus_To_Epistemic_Desires,
TMap_Belief_To_Salience_Stimuli, TMap_Exogenous_Functions_Handler.

Deviation: the Java salience-map loader builds the path with a Windows backslash
(``Dir_Path + "\\\\" + file``), which does not open on Linux/macOS; here ``/`` is used (the
Java run used for the comparison had the same patch).

Kept from Java: a ``NumberFormatException`` in the XML aborts the load (the stack trace is
printed and the entries read so far stay in the map).
"""
from __future__ import annotations

import sys
import traceback
import os
from typing import Callable, Dict, List, Optional

from .xmlio import (descendants, get_document_xml, get_element_text_content, text_content)


class MappedEpistemicDesire:
    """Java: TMapped_Epistemic_Desire."""

    def __init__(self, type_stimulus: str, saliency: float, trigger_condition_formula: str,
                 trigger_condition_names: Optional[List[str]], reward: float, relax_preference: float,
                 list_green_desires_name: Optional[List[str]],
                 list_quality_desires_name: Optional[List[str]],
                 list_beliefs_for_reasoner: Optional[List[str]],
                 list_regions_for_reasoner: Optional[List[str]]):
        self.type_stimulus = type_stimulus
        self.saliency = saliency
        self.trigger_condition_formula = trigger_condition_formula
        self.reward = reward
        self.relax_preference = relax_preference
        self.trigger_condition_names: List[str] = list(trigger_condition_names or [])
        self.list_green_desires_name: List[str] = list(list_green_desires_name or [])
        self.list_quality_desires_name: List[str] = list(list_quality_desires_name or [])
        self.list_beliefs_for_reasoner: List[str] = list(list_beliefs_for_reasoner or [])
        self.list_regions_for_reasoner: List[str] = list(list_regions_for_reasoner or [])

    def __repr__(self) -> str:
        return (f"TMapped_Epistemic_Desire{{Type_Stimulus='{self.type_stimulus}', "
                f"Saliency={self.saliency}, Reward={self.reward}, "
                f"Relax_Preference={self.relax_preference}, "
                f"Green_Desires=[{', '.join(self.list_green_desires_name)}], "
                f"Quality_Desires=[{', '.join(self.list_quality_desires_name)}]}}")


def _parse_double(text: str) -> float:
    if "_" in text:
        raise ValueError(text)           # Java Double.parseDouble rejects underscores
    return float(text)


def _desire_names(parent, parent_tag: str) -> List[str]:
    parents = descendants(parent, parent_tag)
    if parents:
        return [text_content(n) for n in descendants(parents[0], "DesireName")]
    return []


class MapStimulusToEpistemicDesires:
    """Java: TMap_Stimulus_To_Epistemic_Desires."""

    def __init__(self) -> None:
        self.list_mapped_epistemic_desires: Dict[str, MappedEpistemicDesire] = {}
        self.xml_file_path: str = ""

    def add_stimulus_type_to_epistemic_desire(self, stimulus_type: str,
                                              desire: MappedEpistemicDesire) -> None:
        self.list_mapped_epistemic_desires[stimulus_type] = desire

    def set_file_path(self, value: str) -> None:
        self.xml_file_path = value

    def load_mapped_epistemic_desires(self) -> None:
        """Load the XML of mapped epistemic desires (stimulus type -> saliency, trigger formula, reward, ...);
        prints an error and returns if the file is missing.
        """
        if not os.path.exists(self.xml_file_path):
            print(f"Error: The XML file '{self.xml_file_path}' doesn't exist!", file=sys.stderr)
            return
        import xml.etree.ElementTree as ET
        try:
            root = ET.parse(self.xml_file_path).getroot()
            self.list_mapped_epistemic_desires.clear()
            for element in root.iter("MappedDesire"):
                type_stimulus = get_element_text_content(element, "StimulusType")
                saliency = _parse_double(get_element_text_content(element, "Saliency"))
                reward = _parse_double(get_element_text_content(element, "Reward"))
                relax = _parse_double(get_element_text_content(element, "RelaxPreference"))
                formula = get_element_text_content(element, "TriggerConditionFormula")
                self.list_mapped_epistemic_desires[type_stimulus] = MappedEpistemicDesire(
                    type_stimulus, saliency, formula,
                    _desire_names(element, "TriggerConditionNames"), reward, relax,
                    _desire_names(element, "GreenDesires"), _desire_names(element, "QualityDesires"),
                    _desire_names(element, "Beliefs_for_Reasoner"), None)
        except (ET.ParseError, OSError, ValueError):
            traceback.print_exc()

    def get_mapped_epistemic_desires(self) -> Dict[str, MappedEpistemicDesire]:
        return self.list_mapped_epistemic_desires


class MapBeliefToSalienceStimuli:
    """Java: TMap_Belief_To_Salience_Stimuli."""

    def __init__(self) -> None:
        self.list_mapped_salience_stimuli: Dict[str, float] = {}
        self.xml_file_path: str = ""
        self.default_file_name: str = "Map_Belief_To_Salience_Stimuli.xml"

    def add_type_belief_to_salience_stimuli(self, stimulus_type: str, saliency: float) -> None:
        self.list_mapped_salience_stimuli[stimulus_type] = saliency

    def set_file_path(self, value: str) -> None:
        self.xml_file_path = value

    def load_mapped_epistemic_desires(self, dir_path: str) -> None:
        """Load ``Map_Belief_To_Salience_Stimuli.xml`` from ``dir_path`` into the belief-type -> saliency map
        (decimal commas accepted).
        """
        filename = dir_path + "/" + self.default_file_name
        self.set_file_path(filename)
        if not os.path.exists(self.xml_file_path):
            print(f"Error: The XML file '{self.xml_file_path}' doesn't exist!", file=sys.stderr)
            return
        import xml.etree.ElementTree as ET
        try:
            root = ET.parse(self.xml_file_path).getroot()
            self.list_mapped_salience_stimuli.clear()
            for element in root.iter("Map_Belief_To_Salience_Stimulus"):
                type_stimulus = get_element_text_content(element, "Belief_Type")
                saliency = _parse_double(get_element_text_content(element, "Value").replace(",", "."))
                self.list_mapped_salience_stimuli[type_stimulus] = saliency
        except (ET.ParseError, OSError, ValueError):
            traceback.print_exc()

    def get_mapped_stimuli(self) -> Dict[str, float]:
        return self.list_mapped_salience_stimuli


class MapExogenousFunctionsHandler:
    """Java: TMap_Exogenous_Functions_Handler (stimulus type -> function(gw, stimulus) -> epistemic desire).
    """

    def __init__(self) -> None:
        self.list_functions: Dict[str, Callable] = {}

    def register_epistemic_function(self, stimulus_type: Optional[str], func: Optional[Callable]) -> None:
        if stimulus_type is None or stimulus_type.strip() == "" or func is None:
            raise ValueError("Invalid key or function entered in 'TStimulus_to_Function_Manager.")
        self.list_functions[stimulus_type] = func

    def unregister_epistemic_function(self, stimulus_type: Optional[str]) -> None:
        if stimulus_type is None or stimulus_type.strip() == "":
            raise ValueError("Invalid key or function entered in 'TStimulus_to_Function_Manager'.")
        self.list_functions.pop(stimulus_type, None)

    def execute_epistemic_function(self, global_workspace, stimulus):
        """Run the function registered for the stimulus' belief type; None if the type is empty or has no
        function.
        """
        type_belief = stimulus.get_type_belief()
        if type_belief is None or type_belief.strip() == "":
            print("Error: The key provided for execution is null or empty.", file=sys.stderr)
            return None
        func = self.list_functions.get(type_belief)
        if func is not None:
            return func(global_workspace, stimulus)
        return None

    def get_mapped_functions(self) -> Dict[str, Callable]:
        return self.list_functions

    def clear(self) -> None:
        self.list_functions.clear()
