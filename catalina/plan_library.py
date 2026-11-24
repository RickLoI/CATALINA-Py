"""GLITTER plan library: a trie keyed by goals -> pre-conditions -> qualities.

Java: TTrieNode, TGLITTER_Trie (implements IPlanner).

Kept from Java (observable behaviour)
-------------------------------------
* ``create_plan`` always returns ``False`` on the normal path (the Java ``result`` is never
  set to true).
* ``get_plans`` raises ``JavaNullPointerError`` when the path exists but the final node has no
  tasks (Java: NullPointerException iterating ``Layer_Tasks == null``).
* Adding a pre-condition node REPLACES the value map already stored under that name.
* Pre-condition values are keys of a Java ``HashMap<Object, TTrieNode>``: ``Integer 1``,
  ``Double 1.0`` and ``Boolean true`` are different keys. ``_jkey`` reproduces that.
* The quality layer ignores the value (only the quality/green desire name selects the node).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .desires import AttentionalDesire, EpistemicDesire, PracticalDesire
from .model import Predicate
from .plan import Action, Intention
from .sorters import BooleanExpressionSorter


class JavaNullPointerError(RuntimeError):
    """Stands for a Java NullPointerException that the original code would raise."""


def _jkey(value: Any) -> Tuple[str, Any]:
    """Key emulating Java ``Object.equals`` between boxed values (type matters)."""
    return (type(value).__name__, value)


def _sorted_names(names) -> List[str]:
    """``Comparator.nullsFirst(naturalOrder())`` over Strings."""
    return sorted(names, key=lambda s: (s is not None, s if s is not None else ""))


class TrieNode:
    """Java: TTrieNode."""

    def __init__(self) -> None:
        self.layer_goals: Optional[Dict[str, "TrieNode"]] = None
        self.layer_pre_conditions: Optional[Dict[str, Dict[Tuple[str, Any], "TrieNode"]]] = None
        self.layer_quality_of_solution: Optional[Dict[str, "TrieNode"]] = None
        self.layer_tasks: Optional[List[Action]] = None
        self.data: Any = None
        self.layer_final_state: Optional[str] = None
        self.name: Optional[str] = None

    def clear(self) -> None:
        self.__init__()

    def get_layer_goals(self):
        return self.layer_goals

    def get_layer_quality(self):
        return self.layer_quality_of_solution

    def get_layer_preconditions(self):
        return self.layer_pre_conditions

    def add_node_goal(self, name: str) -> "TrieNode":
        node = TrieNode()
        node.data = name
        node.name = name
        if self.layer_goals is None:
            self.layer_goals = {}
        self.layer_goals[name] = node
        return node

    def add_node_pre_condition(self, name: str, value: Any) -> "TrieNode":
        node = TrieNode()
        node.data = value
        node.name = name
        if self.layer_pre_conditions is None:
            self.layer_pre_conditions = {}
        self.layer_pre_conditions[name] = {_jkey(value): node}   # replaces (Java)
        return node

    def add_node_quality_solution(self, name: str, value: Any) -> "TrieNode":
        node = TrieNode()
        node.data = value
        node.name = name
        if self.layer_quality_of_solution is None:
            self.layer_quality_of_solution = {}
        self.layer_quality_of_solution[name] = node
        return node

    def get_data(self) -> Any:
        return self.data

    def get_name(self) -> Optional[str]:
        return self.name

    def get_layer_tasks(self) -> Optional[List[Action]]:
        return self.layer_tasks

    def get_layer_final_state(self) -> Optional[str]:
        return self.layer_final_state

    def insert_tasks(self, actions: List[Action]) -> None:
        if self.layer_tasks is None:
            self.layer_tasks = []
        self.layer_tasks.clear()
        self.layer_tasks.extend(actions)

    def set_layer_final_state(self, value: str) -> None:
        self.layer_final_state = value


class GlitterTrie:
    """Java: TGLITTER_Trie."""

    def __init__(self) -> None:
        self.root = TrieNode()

    @staticmethod
    def _quality_map(desire: PracticalDesire) -> Dict[str, Any]:
        quality: Dict[str, Any] = {}
        for q in desire.get_list_quality_standing_desire():
            quality[q.get_name()] = q.get_constraint().get_object_complement()
        for g in desire.get_list_green_standing_desire():
            quality[g.get_name()] = g.get_constraint().get_object_complement()
        return quality

    def get_plans(self, attentional_desire: AttentionalDesire,
                  preconditions: List[Predicate]) -> List[Action]:
        """Find the stored plan for a practical desire: walk the trie by the sorted goals of its final state,
        then by preconditions and quality values; returns the action list (empty if none).
        """
        result: List[Action] = []
        if isinstance(attentional_desire, EpistemicDesire):
            return result
        desire: PracticalDesire = attentional_desire
        final_state = desire.get_final_state().get_formula()
        goals = list(BooleanExpressionSorter.sort_expression(final_state).get_product_list())
        pre_cond: Dict[str, Any] = {}
        for predicate in preconditions:
            pre_cond[predicate.get_name()] = predicate.get_object_complement()
        quality = self._quality_map(desire)

        node = self.root
        for index_name in goals:
            temp = node.get_layer_goals().get(index_name) if node.get_layer_goals() is not None else None
            if temp is None:
                return result
            node = temp

        for index_name in _sorted_names(pre_cond.keys()):
            index_value = pre_cond[index_name]
            values = None
            if node.get_layer_preconditions() is not None:
                values = node.get_layer_preconditions().get(index_name)
            if values is not None and values.get(_jkey(index_value)) is not None:
                node = values[_jkey(index_value)]
            else:
                return result

        for index_name in _sorted_names(quality.keys()):
            temp = None
            if node.get_layer_quality() is not None:
                temp = node.get_layer_quality().get(index_name)
            if temp is None:
                return result
            node = temp

        if node.get_layer_tasks() is None:
            raise JavaNullPointerError("Layer_Tasks is null (no plan stored at this trie node)")
        result.extend(node.get_layer_tasks())
        return result

    def create_plan(self, intention: Intention) -> bool:
        """Store the actions of the selected option of an intention in the trie (goals -> preconditions ->
        quality). False for epistemic desires or when no option is selected; the first action's
        preconditions index the plan.
        """
        result = False
        if isinstance(intention.get_active_desire(), EpistemicDesire):
            return result
        desire: PracticalDesire = intention.get_active_desire()
        option_id = intention.get_selected_option_id()
        if desire is None:
            return False
        if option_id < 0:
            return False
        option = desire.get_list_options()[option_id]

        final_state = desire.get_final_state().get_formula()
        goals = list(BooleanExpressionSorter.sort_expression(final_state).get_product_list())

        actions = option.get_plan_actions()
        if not actions:
            raise IndexError("NoSuchElementException: the option has no actions")
        pre_cond: Dict[str, Any] = {}
        for predicate in actions[0].get_pre_conditions():
            pre_cond[predicate.get_name()] = predicate.get_object_complement()
        tasks = [action.clone() for action in actions]
        quality = self._quality_map(desire)

        node = self.root
        for index_name in goals:
            temp = node.get_layer_goals().get(index_name) if node.get_layer_goals() is not None else None
            node = temp if temp is not None else node.add_node_goal(index_name)

        for index_name in _sorted_names(pre_cond.keys()):
            index_value = pre_cond[index_name]
            values = None
            if node.get_layer_preconditions() is not None:
                values = node.get_layer_preconditions().get(index_name)
            if values is not None and values.get(_jkey(index_value)) is not None:
                node = values[_jkey(index_value)]
            else:
                node = node.add_node_pre_condition(index_name, index_value)

        for index_name in _sorted_names(quality.keys()):
            index_value = quality[index_name]
            temp = None
            if node.get_layer_quality() is not None:
                temp = node.get_layer_quality().get(index_name)
            node = temp if temp is not None else node.add_node_quality_solution(index_name, index_value)

        node.insert_tasks(tasks)
        node.set_layer_final_state(final_state)
        return result
