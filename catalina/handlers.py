"""Function registries ("handlers") used by the executive functions.

Java classes: TPerception_Processing_Sensor_Function_Handler, TInformation_Extraction_Function_Handler,
TStimulus_Filtering_Manipulate_Stimulus_Function_Handler, TBelief_Inhibition_Function_Handler,
TRegion_Inhibition_Function_Handler, TExogenous_Attentional_Desires_Function_Handler (+ its result
class), TMeans_End_Epistemic_Functions_Handler, TMeans_End_Practical_Functions_Handler,
TGreen_Desires_Filter_Function_Handler, TAction_Execution_Function_Handler (+
TAction_Execution_Result), TResource_Managment_Practical_Functions_Handler, TTriple_Object.

A handler maps a name (sensor, stimulus type, desire name, belief type, action name...) to a Python
callable. The callables get the same arguments as the Java functional interfaces:

* sensor function            ``f(sensor) -> list[Perception]``
* information extraction     ``f(perception, map_beliefs, map_regions) -> list[Stimulus]``
* stimulus manipulation      ``f(stimulus, regions) -> Stimulus``
* belief inhibition          ``f(attentional_desire, map_beliefs) -> set/list of belief names``
* region inhibition          ``f(intention, map_beliefs, map_regions) -> set/list of region names``
* exogenous (practical)      ``f(stimulus, beliefs, recall_belief) -> ExogenousPromotionResult``
* means-end epistemic        ``f(epistemic_desire, beliefs, regions, intentions, planner) -> list[Option]``
* means-end practical        ``f(practical_desire, beliefs, regions, intentions, planner) -> list[Option]``
* green filter               ``f(green_desire, desire, beliefs, regions, intentions) -> list[Option]``
* action execution           ``f(global_workspace, action, beliefs) -> ActionExecutionResult``
* resource management        ``f(critical_belief, beliefs, intentions) -> TripleObject``

Java behaviour kept: registration rejects null / blank names and null functions with
``ValueError`` (Java IllegalArgumentException); executing a name without function returns the
"empty" result; ``System.err`` messages go to ``sys.stderr``.
"""
from __future__ import annotations

import sys
from typing import Any, Callable, Dict, List, Optional


def _blank(name: Optional[str]) -> bool:
    return name is None or name.strip() == ""


def _err(message: str) -> None:
    print(message, file=sys.stderr)


class TripleObject:
    """Java: TTriple_Object."""

    def __init__(self, first: Any = None, second: Any = None, third: Any = None):
        self.first = first
        self.second = second
        self.third = third

    def get_object_first(self) -> Any:
        return self.first

    def get_object_second(self) -> Any:
        return self.second

    def get_object_third(self) -> Any:
        return self.third

    def set_object_first(self, value: Any) -> None:
        self.first = value

    def set_object_second(self, value: Any) -> None:
        self.second = value

    def set_object_third(self, value: Any) -> None:
        self.third = value


# ---------------------------------------------------------------------------------- perception
class PerceptionProcessingSensorFunctionHandler:
    """Registry sensor name -> function that polls the sensor and returns perceptions."""
    def __init__(self) -> None:
        self.registered_functions: Dict[str, Callable] = {}

    def register_function(self, sensor: Optional[str], func: Optional[Callable]) -> None:
        if sensor is None or func is None:
            raise ValueError("Invalid Sensor or function for registration.")
        self.registered_functions[sensor] = func

    def unregister_function(self, sensor: Optional[str]) -> bool:
        if sensor is None:
            return False
        return self.registered_functions.pop(sensor, None) is not None

    def execute_function_for_sensor(self, sensor: Optional[str]) -> List[Any]:
        """Run the function registered for ``sensor`` and return its perceptions (empty list if none)."""
        last: List[Any] = []
        if sensor is None:
            _err("Error: Sensor provided for execution is null.")
            return last
        func = self.registered_functions.get(sensor)
        if func is None:
            return last
        temp = func(sensor)
        if temp is not None:
            last.extend(temp)
            for perception in last:
                perception.source = sensor          # Java Set_Source
        return last


class InformationExtractionFunctionHandler:
    """Registry sensor name -> function that turns a raw perception into stimuli."""
    def __init__(self) -> None:
        self.registered_functions: Dict[str, Callable] = {}

    def register_function(self, sensor: Optional[str], func: Optional[Callable]) -> None:
        if sensor is None or func is None:
            raise ValueError("Invalid Sensor or function for registration.")
        self.registered_functions[sensor] = func

    def unregister_function(self, sensor: Optional[str]) -> bool:
        if sensor is None:
            return False
        return self.registered_functions.pop(sensor, None) is not None

    def execute_function_for_raw_data(self, sensor: Optional[str], perception: Any,
                                      map_uninhibited_beliefs: Dict[str, Any],
                                      map_uninhibited_regions: Dict[str, Any]) -> List[Any]:
        """Run the extraction function of ``sensor`` on a perception; returns the stimuli it produces."""
        last: List[Any] = []
        if sensor is None:
            _err("Error: Sensor provided for execution is null.")
            return last
        func = self.registered_functions.get(sensor)
        if func is not None:
            temp = func(perception, map_uninhibited_beliefs, map_uninhibited_regions)
            if temp is not None:
                last.extend(temp)
        return last


class StimulusFilteringManipulateStimulusFunctionHandler:
    """Registry stimulus type -> function that may manipulate a stimulus (e.g. its saliency) given the
    inhibited regions.
    """
    def __init__(self) -> None:
        self.registered_functions: Dict[str, Callable] = {}

    def register_function(self, stimulus_type: Optional[str], func: Optional[Callable]) -> None:
        if _blank(stimulus_type) or func is None:
            raise ValueError("Invalid Stimulus Type or function for registration.")
        self.registered_functions[stimulus_type] = func

    def unregister_function(self, stimulus_type: Optional[str]) -> bool:
        if _blank(stimulus_type):
            return False
        return self.registered_functions.pop(stimulus_type, None) is not None

    def execute_function_for_stimulus(self, stimulus: Any, regions: List[Any]) -> Any:
        """Run the manipulation function of the stimulus type (if any); the original stimulus is kept when the
        function returns None.
        """
        generated = stimulus
        if generated is None or generated.get_type_belief() is None or generated.get_type_belief().strip() == "":
            _err("Error: Stimulus provided for execution is null.")
            return generated
        func = self.registered_functions.get(stimulus.get_type_belief())
        if func is not None:
            generated = func(stimulus, regions)
            if generated is None:
                generated = stimulus
        return generated


# ---------------------------------------------------------------------------------- inhibition
class BeliefInhibitionFunctionHandler:
    """Registry desire name -> function that returns the names of the beliefs to inhibit/uninhibit for it."""
    def __init__(self) -> None:
        self.registered_functions: Dict[str, Callable] = {}

    def register_belief_inhibition_function(self, name: Optional[str], func: Optional[Callable]) -> None:
        if _blank(name) or func is None:
            raise ValueError("Invalid beliefType or function for registration.")
        self.registered_functions[name] = func

    def unregister_belief_inhibition_function(self, name: Optional[str]) -> bool:
        if _blank(name):
            return False
        return self.registered_functions.pop(name, None) is not None

    def execute_function_for_desire(self, desire_name: Optional[str], attentional_desire: Any,
                                    map_beliefs: Dict[str, Any]) -> Dict[str, None]:
        """Returns the belief names as an insertion-ordered dict (Java HashSet<String>)."""
        results: Dict[str, None] = {}
        if desire_name is None or desire_name == "":
            _err("Error: Name for Belief Inhibition Function provided for execution is null.")
            return results
        func = self.registered_functions.get(desire_name)
        if func is not None:
            temp = func(attentional_desire, map_beliefs)
            if temp is not None:
                for name in temp:
                    if name is not None:
                        results[name] = None
        return results


class RegionInhibitionFunctionHandler:
    """Registry intention/desire name -> function that returns the names of the regions to uninhibit for it.
    """
    def __init__(self) -> None:
        self.registered_functions: Dict[str, Callable] = {}

    def register_region_inhibition_function(self, name: Optional[str], func: Optional[Callable]) -> None:
        if _blank(name) or func is None:
            raise ValueError("Invalid beliefType or function for registration.")
        self.registered_functions[name] = func

    def unregister_region_inhibition_function(self, name: Optional[str]) -> bool:
        if _blank(name):
            return False
        return self.registered_functions.pop(name, None) is not None

    def execute_function_for_desire(self, name: Optional[str], intention: Any,
                                    map_beliefs: Dict[str, Any], map_regions: Dict[str, Any]
                                    ) -> Optional[Dict[str, None]]:
        """Run the region-inhibition function for ``name``; returns the region names (ordered dict used as a
        set). A blank name returns None, like Java (the caller then fails).
        """
        if name is None or name == "":
            _err("Error: Name for Belief Inhibition Function provided for execution is null.")
            return None                              # Java returns null (the caller then NPEs)
        results: Dict[str, None] = {}
        func = self.registered_functions.get(name)
        if func is not None:
            temp = func(intention, map_beliefs, map_regions)
            if temp is not None:
                for region_name in temp:
                    results[region_name] = None
        return results


# ---------------------------------------------------------------------------------- desire handler
class ExogenousPromotionResult:
    """Java: TExogenous_Attentional_Desires_Promotion_Function_Result."""

    def __init__(self) -> None:
        self.result: bool = False
        self.practical_desires_data: List[Any] = []
        self.stimuli: List[Any] = []

    def set_result(self, value: bool) -> None:
        self.result = value

    def get_result(self) -> bool:
        return self.result

    def set_practical_desires_data(self, value: Optional[List[Any]]) -> None:
        self.practical_desires_data.clear()
        if value:
            self.practical_desires_data.extend(value)

    def add_practical_desires_data(self, value: Optional[List[Any]]) -> None:
        if value:
            self.practical_desires_data.extend(value)

    def get_practical_desires_data(self) -> List[Any]:
        return self.practical_desires_data

    def get_stimuli(self) -> List[Any]:
        return self.stimuli

    def set_stimuli(self, values: Optional[List[Any]]) -> None:
        self.stimuli.clear()
        if values:
            self.stimuli.extend(values)

    def add_stimuli(self, values: Optional[List[Any]]) -> None:
        if values:
            self.stimuli.extend(values)

    def clear(self) -> None:
        self.result = False
        self.practical_desires_data.clear()
        self.stimuli.clear()


class ExogenousAttentionalDesiresFunctionHandler:
    """Registry stimulus type -> function that decides which desire to raise (and which beliefs to change) for
    it.
    """
    def __init__(self) -> None:
        self.registered_functions: Dict[str, Callable] = {}
        self.recall_belief_function: Optional[Callable] = None

    def register_function(self, stimulus_type: Optional[str], func: Optional[Callable]) -> None:
        if _blank(stimulus_type) or func is None:
            raise ValueError("Invalid Sensor or function for registration.")
        self.registered_functions[stimulus_type] = func

    def unregister_function(self, stimulus_type: Optional[str]) -> bool:
        if _blank(stimulus_type):
            return False
        return self.registered_functions.pop(stimulus_type, None) is not None

    def execute_function_for_desire_to_raise(self, stimulus: Any, beliefs: Dict[str, Any]
                                             ) -> ExogenousPromotionResult:
        """Run the exogenous-promotion function of the stimulus type; returns an ``ExogenousPromotionResult``
        (empty if none).
        """
        result = ExogenousPromotionResult()
        if stimulus is None or stimulus.get_type_belief().strip() == "":
            _err("Error: the Stimulus provided for execution is null.")
            return result
        func = self.registered_functions.get(stimulus.get_type_belief())
        if func is not None:
            temp = func(stimulus, beliefs, self.recall_belief_function)
            if temp is not None:
                result = temp
        return result

    def set_recall_belief(self, recall_belief: Optional[Callable]) -> None:
        if recall_belief is not None:
            self.recall_belief_function = recall_belief


# ---------------------------------------------------------------------------------- reasoner
class MeansEndEpistemicFunctionsHandler:
    """Registry belief type -> means-end function of an epistemic desire (returns options)."""
    def __init__(self) -> None:
        self.registered_functions: Dict[str, Callable] = {}

    def register_epistemic_function(self, belief_type: Optional[str], func: Optional[Callable]) -> None:
        if _blank(belief_type) or func is None:
            raise ValueError("Invalid beliefType or function for registration.")
        self.registered_functions[belief_type] = func

    def unregister_epistemic_function(self, belief_type: Optional[str]) -> bool:
        if _blank(belief_type):
            return False
        return self.registered_functions.pop(belief_type, None) is not None

    def execute_function_for_desire(self, epistemic_desire: Any, beliefs, regions, intentions,
                                    planner, data_getter=None) -> List[Any]:
        """Run the means-end function of the epistemic desire's belief type; returns the options (empty list on
        errors).
        """
        result: List[Any] = []
        if epistemic_desire is None:
            _err("Error: TEpistemic_Desire provided for execution is null.")
            return result
        belief_type = epistemic_desire.get_belief().get_type_belief()
        if belief_type is None or belief_type.strip() == "":
            _err("Error: Associated Belief Type is null or empty in TEpistemic_Desire: "
                 + str(epistemic_desire))
            return result
        func = self.registered_functions.get(belief_type)
        if func is not None:
            temp = func(epistemic_desire, beliefs, regions, intentions, planner)
            if temp is not None:
                result.extend(o for o in temp if o is not None)
        return result


class MeansEndPracticalFunctionsHandler:
    """Registry desire name -> means-end function of a practical desire (returns options)."""
    def __init__(self) -> None:
        self.registered_functions: Dict[str, Callable] = {}

    def register_practical_function(self, desire_name: Optional[str], func: Optional[Callable]) -> None:
        if _blank(desire_name) or func is None:
            raise ValueError("Invalid beliefType or function for registration.")
        self.registered_functions[desire_name] = func

    def unregister_practical_function(self, desire_name: Optional[str]) -> bool:
        if _blank(desire_name):
            return False
        return self.registered_functions.pop(desire_name, None) is not None

    def execute_function_for_desire(self, practical_desire: Any, beliefs, regions, intentions,
                                    planner) -> List[Any]:
        """Run the means-end function registered for the practical desire's name; returns the options (empty
        list on errors).
        """
        result: List[Any] = []
        if practical_desire is None:
            _err("Error: TEpistemic_Desire provided for execution is null.")
            return result
        desire_name = practical_desire.get_name()
        if desire_name is None or desire_name.strip() == "":
            _err("Error: Associated Belief Type is null or empty in TEpistemic_Desire: "
                 + str(practical_desire))
            return result
        func = self.registered_functions.get(desire_name)
        if func is not None:
            temp = func(practical_desire, beliefs, regions, intentions, planner)
            if temp is not None:
                result.extend(temp)
        return result


class GreenDesiresFilterFunctionHandler:
    """Registry green-desire type -> function that filters the options of a desire."""
    def __init__(self) -> None:
        self.registered_functions: Dict[str, Callable] = {}

    def register_function(self, green_name: Optional[str], func: Optional[Callable]) -> None:
        if _blank(green_name) or func is None:
            raise ValueError("Invalid beliefType or function for registration.")
        self.registered_functions[green_name] = func

    def unregister_function(self, green_name: Optional[str]) -> bool:
        if _blank(green_name):
            return False
        return self.registered_functions.pop(green_name, None) is not None

    def execute_function_for_desire(self, green_desire: Any, desire: Any, beliefs, regions,
                                    intentions) -> List[Any]:
        """Apply the filter of the green desire's type to the options of ``desire``; without a function the
        options are returned unchanged.
        """
        result = list(desire.get_list_options())
        if green_desire is None:
            _err("Error: Green Desire provided for execution is null.")
            return result
        green_type = green_desire.get_type_green_standing_desire()
        if green_type is None or green_type.strip() == "":
            _err("Error: Associated Green Desire Name is null or empty in TEpistemic_Desire: " + str(desire))
            return result
        func = self.registered_functions.get(green_type)
        if func is not None:
            temp = func(green_desire, desire, beliefs, regions, intentions)
            if temp is not None:
                result = list(temp)
        return result


# ---------------------------------------------------------------------------------- switching
class ActionExecutionResult:
    """Java: TAction_Execution_Result."""

    def __init__(self) -> None:
        self.result: bool = False
        self.beliefs_to_change: Dict[str, Any] = {}
        self.practical_desires: List[Any] = []
        self.stimuli: List[Any] = []
        self.beliefs_to_monitor: Dict[str, Any] = {}
        self.action: Any = None

    def clear(self) -> None:           # Java does not clear Beliefs_to_Monitor
        self.result = False
        self.beliefs_to_change.clear()
        self.practical_desires.clear()
        self.stimuli.clear()

    def set_result(self, value: bool) -> None:
        self.result = value

    def set_beliefs_to_change(self, value: Dict[str, Any]) -> None:
        self.beliefs_to_change.clear()
        self.beliefs_to_change.update(value)

    def set_beliefs_to_wait(self, value: Dict[str, Any]) -> None:
        self.beliefs_to_monitor.clear()
        self.beliefs_to_monitor.update(value)

    def set_practical_desires(self, value: List[Any]) -> None:
        self.practical_desires.clear()
        self.practical_desires.extend(value)

    def set_stimulu(self, value: List[Any]) -> None:    # sic (Java name)
        self.stimuli.clear()
        self.stimuli.extend(value)

    def get_result(self) -> bool:
        return self.result

    def get_beliefs_to_change(self) -> Dict[str, Any]:
        return self.beliefs_to_change

    def get_beliefs_to_monitor(self) -> Dict[str, Any]:
        return self.beliefs_to_monitor

    def get_practical_desires(self) -> List[Any]:
        return self.practical_desires

    def get_stimuli(self) -> List[Any]:
        return self.stimuli


class ActionExecutionFunctionHandler:
    """Registry action name -> function that executes the action (receives the Global Workspace, the action and
    the beliefs).
    """
    def __init__(self) -> None:
        self.global_workspace: Any = None
        self.registered_functions: Dict[str, Callable] = {}

    def register_function(self, action_name: Any, func: Optional[Callable]) -> None:
        if not isinstance(action_name, str) and action_name is not None:   # Java overload (TAction)
            action_name = action_name.get_action_name()
        if _blank(action_name) or func is None:
            raise ValueError("Invalid beliefType or function for registration.")
        self.registered_functions[action_name] = func

    def unregister_function(self, action_name: Optional[str]) -> bool:
        if _blank(action_name):
            return False
        return self.registered_functions.pop(action_name, None) is not None

    def execute_function_for_desire(self, action: Any, beliefs: Dict[str, Any]) -> ActionExecutionResult:
        """Run the function registered for the action's name; returns an ``ActionExecutionResult`` (a failed
        one if there is no function).
        """
        result = ActionExecutionResult()
        if action is None:
            _err("Error: Action provided for execution is null.")
            return result
        action_name = action.get_action_name()
        if action_name is None or action_name.strip() == "":
            _err("Error: Associated Action Name is null or empty in Action Name: " + str(action_name))
            return result
        func = self.registered_functions.get(action_name)
        if func is not None:
            temp = func(self.global_workspace, action, beliefs)
            if temp is not None:
                result = temp
            return result
        print("\nWARN: No Plan Execution Function registered for the Action Name: '" + action_name + "'.")
        return result

    def set_global_workspace(self, gw: Any) -> None:
        if gw is not None:
            self.global_workspace = gw


# ---------------------------------------------------------------------------------- resources
class ResourceManagmentPracticalFunctionsHandler:
    """Registry critical-belief type -> resource-management function."""
    def __init__(self) -> None:
        self.registered_functions: Dict[str, Callable] = {}

    def register_function(self, belief_type: Any, func: Optional[Callable]) -> None:
        if not isinstance(belief_type, str) and belief_type is not None:    # Java overload (TBelief)
            belief_type = belief_type.get_type_belief()
        if _blank(belief_type) or func is None:
            raise ValueError("Invalid belief type or function for registration.")
        self.registered_functions[belief_type] = func

    def unregister_function(self, belief_type: Optional[str]) -> bool:
        if _blank(belief_type):
            return False
        return self.registered_functions.pop(belief_type, None) is not None

    def execute_function_for_desire(self, important_belief: Any, beliefs, intentions) -> Optional[TripleObject]:
        """Run the resource-management function of the critical belief's type; returns a TripleObject (desire,
        signal, data) or None on errors.
        """
        if important_belief is None:
            _err("Error: Important Belief provided for execution is null.")
            return None
        belief_type = important_belief.get_type_belief()
        if belief_type is None or belief_type.strip() == "":
            _err("Error: Associated Belief Type is null or empty in important belief: " + str(important_belief))
            return None
        if beliefs is None:
            _err("Error: Beliefs provided for execution are null.")
            return None
        if intentions is None:
            _err("Error: Intentions provided for execution are null.")
            return None
        func = self.registered_functions.get(belief_type)
        if func is not None:
            return func(important_belief, beliefs, intentions)
        return None
