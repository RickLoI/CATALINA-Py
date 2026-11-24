"""Executive Reasoner Function.

Java: TExecutive_Reasoner_Function, TMeans_End_Reasoner, TMeans_End_Reasoner_Data_Getter,
TFinally_Operator, TFiltering_Process, TDeliberation_Process.

When active desires change: means-end reasoning produces the options of every active desire that
is not already an intention (through functions registered by desire name -practical- or by belief
type -epistemic-); the finally operator and the green/quality filters prune them; the deliberation
function (supplied by the application, none by default) chooses the intentions, which are sorted
by saliency and published with ``set_selected_intentions``.

Java behaviour kept on purpose:
* ``sort_selected_intentions`` keeps only the FIRST intention that has options (the most salient)
  followed by the ones without options; further intentions with options are dropped.
* ``FinallyOperator`` keeps only the options whose ``satisfied_time`` is set and inside the
  finally interval; options without satisfied time are discarded.
* The belief/region names a desire asks for come from ``get_beliefs_name_for_reasoner`` (with
  the epistemic loader quirk 1, one glued string).
* ``beliefs`` flag short-circuits: the ``uninhibited_data`` flag is cleared only if the
  ``beliefs`` flag was not set.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .agent_thread import AgentBaseThread
from .desires import EpistemicDesire, PracticalDesire
from .enums import TypeUpdateContract as C
from .handlers import (GreenDesiresFilterFunctionHandler, MeansEndEpistemicFunctionsHandler,
                       MeansEndPracticalFunctionsHandler)


class MeansEndReasonerDataGetter:
    """Gives the means-end functions access to beliefs/regions of the long-term memory by name (used by
    epistemic functions).
    """
    def __init__(self, owner: "ExecutiveReasonerFunction"):
        self.owner = owner

    def get_selected_beliefs(self, beliefs_names) -> Dict[str, Any]:
        return dict(self.owner.get_global_workspace().get_selected_beliefs_from_ltm(set(beliefs_names)))

    def get_selected_regions(self, regions_names) -> Dict[str, Any]:
        return dict(self.owner.get_global_workspace().get_selected_regions_from_ltm(set(regions_names)))


class MeansEndReasoner:
    """Generates the options of every active desire not already being pursued, through the functions registered
    by desire name (practical) or belief type (epistemic).
    """
    def __init__(self, owner: "ExecutiveReasonerFunction"):
        self.owner = owner
        self.global_workspace = owner.get_global_workspace()
        self.epistemic_handler = MeansEndEpistemicFunctionsHandler()
        self.practical_handler = MeansEndPracticalFunctionsHandler()
        self.desires_to_filter: List[Any] = []
        self.generate_options_for_practical_desire: Optional[Callable] = None

    def execute(self, active_desires: List[Any]) -> None:
        """Run the means-end function of each active desire that is not already the active desire of an
        intention and store the options in the desire.
        """
        self.desires_to_filter = []
        data_getter = MeansEndReasonerDataGetter(self.owner)
        for desire in active_desires:
            can_analyze = True
            related = desire.get_related_intention()
            if related is not None and related.get_active_desire() is desire:
                can_analyze = False
            if can_analyze:
                options: List[Any] = []
                if isinstance(desire, PracticalDesire):
                    options.extend(self.practical_handler.execute_function_for_desire(
                        desire, self.owner.get_map_beliefs(), self.owner.get_map_regions(),
                        self.owner.get_intentions(), self.global_workspace.plan_library))
                elif isinstance(desire, EpistemicDesire):
                    options.extend(self.epistemic_handler.execute_function_for_desire(
                        desire, self.owner.get_map_beliefs(), self.owner.get_map_regions(),
                        self.owner.get_intentions(), self.global_workspace.plan_library, data_getter))
                else:
                    raise ValueError(f"Unexpected value: {desire}")
                desire.set_list_options(options)
                self.desires_to_filter.append(desire)

    def get_desires_to_filter(self) -> List[Any]:
        result, self.desires_to_filter = list(self.desires_to_filter), []
        return result

    def set_generate_options_for_practical_desire(self, func: Optional[Callable]) -> None:
        self.generate_options_for_practical_desire = func

    def register_epistemic_function(self, belief_type: str, func: Callable) -> None:
        self.epistemic_handler.register_epistemic_function(belief_type, func)

    def unregister_epistemic_function(self, belief_type: str) -> bool:
        return self.epistemic_handler.unregister_epistemic_function(belief_type)

    def register_practical_function(self, desire_name: str, func: Callable) -> None:
        self.practical_handler.register_practical_function(desire_name, func)

    def unregister_practical_function(self, desire_name: str) -> bool:
        return self.practical_handler.unregister_practical_function(desire_name)


class FinallyOperator:
    """Keeps only the options whose satisfied time falls inside the desire's 'finally' interval."""
    def __init__(self, owner: "ExecutiveReasonerFunction"):
        self.owner = owner

    def execute(self, desires_to_filter: List[Any]) -> None:
        """Drop, for each practical desire, the options without a satisfied time or with one outside the
        finally interval.
        """
        for desire in desires_to_filter:
            if isinstance(desire, PracticalDesire):
                options = list(desire.get_list_options())
                operator = desire.get_final_state().get_temporal_operator()
                start = operator.get_start_time()
                end = operator.get_end_time()
                survived: List[Any] = []
                for option in options:
                    satisfied_time = option.get_satisfied_time()
                    if satisfied_time is not None:
                        if satisfied_time >= start and satisfied_time <= end:
                            survived.append(option)
                desire.set_list_options(survived)


class FilteringProcess:
    """Applies the green-desire filters and the quality-desire filter to the options of each desire, then
    broadcasts ``Updated_Active_Desires_with_Options``.
    """
    def __init__(self, owner: "ExecutiveReasonerFunction"):
        self.parent = owner
        self.global_workspace = owner.get_global_workspace()
        self.green_desires_filter_function_handler = GreenDesiresFilterFunctionHandler()
        self.quality_desires_filter_function: Optional[Callable] = None

    def execute(self, desires_to_filter: List[Any]) -> None:
        """For each desire: apply every green filter, then the quality filter (prints a message if none is
        set), then broadcast the options update.
        """
        for desire in desires_to_filter:
            greens = list(desire.get_list_green_standing_desire())
            qualities = list(desire.get_list_quality_standing_desire())
            for green in greens:
                options = self.green_desires_filter_function_handler.execute_function_for_desire(
                    green, desire, self.parent.get_beliefs(), self.parent.get_regions(),
                    self.parent.get_intentions())
                desire.set_list_options(options)
            if self.quality_desires_filter_function is not None:
                options = self.quality_desires_filter_function(
                    desire, self.parent.get_beliefs(), self.parent.get_regions(), self.parent.get_intentions())
                if options is not None:
                    desire.set_list_options(options)
            else:
                print("A Quality Desires Filter Function must be associated to " + str(desire.get_name()))
        self.global_workspace.broadcast_signal(C.Updated_Active_Desires_with_Options)

    def set_quality_desire_filtering_process(self, func: Optional[Callable]) -> None:
        self.quality_desires_filter_function = func

    def register_green_filtering_function(self, green_type: str, func: Callable) -> None:
        self.green_desires_filter_function_handler.register_function(green_type, func)

    def unregister_green_filtering_function(self, green_type: str) -> bool:
        return self.green_desires_filter_function_handler.unregister_function(green_type)


class DeliberationProcess:
    """Calls the application's deliberation function (if any) to choose the intentions among the desires with
    options.
    """
    def __init__(self, owner: "ExecutiveReasonerFunction"):
        self.owner = owner
        self.global_workspace = owner.get_global_workspace()
        self.selected_intentions: List[Any] = []
        self.deliberation_process_function: Optional[Callable] = None

    def execute(self, active_desires: List[Any]) -> None:
        self.selected_intentions = []
        beliefs = dict(self.owner.get_map_beliefs())
        regions = dict(self.owner.get_map_regions())
        intentions = list(self.owner.get_intentions())
        if self.deliberation_process_function is not None:
            self.selected_intentions.extend(
                self.deliberation_process_function(active_desires, beliefs, regions, intentions))

    def get_selected_intentions(self) -> List[Any]:
        result, self.selected_intentions = list(self.selected_intentions), []
        return result

    def set_deliberation_process_function(self, func: Optional[Callable]) -> None:
        self.deliberation_process_function = func


class ExecutiveReasonerFunction(AgentBaseThread):
    """Executive Reasoner thread: means-end reasoning -> finally operator -> filtering -> deliberation ->
    selected intentions (see the module docstring).
    """
    def __init__(self, agent: Any):
        super().__init__(agent, "Executive Reasoner Function")
        self.global_workspace = agent.get_global_workspace()
        self.filtering_process = FilteringProcess(self)
        self.finally_operator = FinallyOperator(self)
        self.means_end_reasoner = MeansEndReasoner(self)
        self.deliberation_process = DeliberationProcess(self)
        self.active_desires: List[Any] = []
        self.desires_to_filter: List[Any] = []
        self.beliefs: List[Any] = []
        self.map_beliefs: Dict[str, Any] = {}
        self.regions: List[Any] = []
        self.map_regions: Dict[str, Any] = {}
        self.intentions: List[Any] = []
        self.list_beliefs_names_for_desires: Dict[str, Any] = {}
        self.list_regions_names_for_desires: Dict[str, Any] = {}

    def insert_in_list_update_contract(self) -> None:
        gw = self.agent.get_global_workspace()
        for contract in (C.Updated_Active_Desires, C.Updated_Beliefs, C.Updated_Uninhibited_Data,
                         C.Updated_Selected_Intentions):
            gw.insert_for_update_contract(contract, self)

    def execute(self) -> None:
        """Runs only when the active desires changed: refresh beliefs/regions/intentions, run means-end,
        finally, filtering and deliberation, and publish the sorted selected intentions.
        """
        mh = self.message_handler
        gw = self.global_workspace
        if not mh.read_value_and_clear("active_desires"):
            return
        selected: List[Any] = []
        self.desires_to_filter = []
        self.active_desires = list(gw.get_unhinibited_active_desires())
        if mh.read_value_and_clear("beliefs") or mh.read_value_and_clear("uninhibited_data"):
            self.beliefs = list(gw.get_uninhibited_beliefs())
            self.map_beliefs = dict(gw.get_map_uninhibited_beliefs())
            self.regions = list(gw.get_uninhibited_regions())
            self.map_regions = dict(gw.get_map_uninhibited_regions())
            self.map_regions.update(self._ensures_regions_for_desires(self.active_desires))
        if mh.read_value_and_clear("selected_intentions"):
            self.intentions = gw.get_selected_intentions()
        self.map_beliefs.update(self._ensures_beliefs_for_desires(self.active_desires))
        self.means_end_reasoner.execute(self.active_desires)
        self.desires_to_filter.extend(self.means_end_reasoner.get_desires_to_filter())
        if len(self.desires_to_filter) > 0:
            self.finally_operator.execute(self.desires_to_filter)
            self.filtering_process.execute(self.desires_to_filter)
            self.deliberation_process.execute(self.desires_to_filter)
            selected.extend(self.deliberation_process.get_selected_intentions())
        if len(selected) > 0:
            selected = self.sort_selected_intentions(selected)
            gw.set_selected_intentions(selected)

    def get_beliefs(self) -> List[Any]:
        return self.beliefs

    def get_map_beliefs(self) -> Dict[str, Any]:
        return self.map_beliefs

    def get_regions(self) -> List[Any]:
        return self.regions

    def get_map_regions(self) -> Dict[str, Any]:
        return self.map_regions

    def get_intentions(self) -> List[Any]:
        return self.intentions

    def get_global_workspace(self) -> Any:
        return self.global_workspace

    # ---- registration API
    def register_green_filtering_function(self, green_type: str, func: Callable) -> None:
        self.filtering_process.register_green_filtering_function(green_type, func)

    def unregister_green_filtering_function(self, green_name: str) -> bool:
        return self.filtering_process.unregister_green_filtering_function(green_name)

    def set_generate_options_for_practical_desire(self, func: Callable) -> None:
        self.means_end_reasoner.set_generate_options_for_practical_desire(func)

    def set_deliberation_process_function(self, func: Callable) -> None:
        self.deliberation_process.set_deliberation_process_function(func)

    def set_quality_desire_filtering_process(self, func: Callable) -> None:
        self.filtering_process.set_quality_desire_filtering_process(func)

    def register_epistemic_function(self, belief_type: str, func: Callable) -> None:
        self.means_end_reasoner.register_epistemic_function(belief_type, func)

    def unregister_epistemic_function(self, belief_type: str) -> bool:
        return self.means_end_reasoner.unregister_epistemic_function(belief_type)

    def register_practical_function(self, desire_name: str, func: Callable) -> None:
        self.means_end_reasoner.register_practical_function(desire_name, func)

    def unregister_practical_function(self, desire_name: str) -> bool:
        return self.means_end_reasoner.unregister_practical_function(desire_name)

    def register_list_beliefs_names_for_desires(self, desire_name: str, beliefs_names) -> None:
        if desire_name is not None and desire_name != "" and beliefs_names is not None:
            self.list_beliefs_names_for_desires[desire_name] = beliefs_names

    def register_list_regions_names_for_desires(self, desire_name: str, regions_names) -> None:
        if desire_name is not None and desire_name != "" and regions_names is not None:
            self.list_regions_names_for_desires[desire_name] = regions_names

    def unregister_list_beliefs_names_for_desires(self, desire_name: str) -> None:
        if desire_name is not None and desire_name != "":
            self.list_beliefs_names_for_desires.pop(desire_name, None)

    def unregister_list_beliefs_names_for_regions(self, desire_name: str) -> None:
        if desire_name is not None and desire_name != "":
            self.list_regions_names_for_desires.pop(desire_name, None)

    # ---- helpers
    def _ensures_beliefs_for_desires(self, active_desires: List[Any]) -> Dict[str, Any]:
        names: Dict[str, None] = {}
        for desire in active_desires:
            names.update(dict.fromkeys(desire.get_beliefs_name_for_reasoner()))
        result = dict(self.global_workspace.get_selected_beliefs_from_ltm(set(names)))
        result.pop(None, None)
        return result

    def _ensures_regions_for_desires(self, active_desires: List[Any]) -> Dict[str, Any]:
        names: Dict[str, None] = {}
        for desire in active_desires:
            names.update(dict.fromkeys(desire.get_regions_name_for_reasoner()))
        result = dict(self.global_workspace.get_selected_regions_from_ltm(set(names)))
        result.pop(None, None)
        return result

    @staticmethod
    def sort_selected_intentions(intentions: List[Any]) -> List[Any]:
        """Order the intentions by desire saliency (descending, intentions without desire last) and keep only
        the first one that has options, followed by those without options (Java behaviour).
        """
        def key(i: Any) -> float:
            return -i.get_active_desire().get_saliency()
        with_desire = [i for i in intentions if i.get_active_desire() is not None]
        without_desire = [i for i in intentions if i.get_active_desire() is None]
        with_desire.sort(key=key)                         # stable, saliency descending
        ordered = with_desire + without_desire            # Java comparator puts null desires last
        first_with_options = None
        new: List[Any] = []
        for intention in ordered:
            desire = intention.get_active_desire()
            if desire is not None:
                if len(desire.get_list_options()) > 0:
                    if first_with_options is None:
                        first_with_options = intention
                else:
                    new.append(intention)
        if first_with_options is not None:
            new.insert(0, first_with_options)
        return new
