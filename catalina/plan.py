"""Plans: actions, options, intentions.

Java: TAction, TOption, TIntention. Only what the plan library (trie) and the Global Workspace
need is ported here; the executive functions of Phase 4/5 add the rest through these classes.

Kept from Java
--------------
* ``Action.copy_action`` does NOT copy ``formula_pre_conditions`` (the Java code copies
  ``Formula_Invariants`` twice), so ``clone()`` yields an action with an empty pre-condition
  formula.
* ``Option.get_previous_action`` returns ``plan_actions[id_current_action]`` (the CURRENT one;
  probable Java bug) and ``None`` when the id is 0.
* ``Intention`` stores ``-1`` when the selected option id is ``None``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Set

from .model import Predicate


class Action:
    """Java: TAction."""

    def __init__(self, params: Optional[List[Any]] = None,
                 preconditions: Optional[List[Predicate]] = None,
                 post_conditions: Optional[List[Predicate]] = None,
                 invariants: Optional[List[Predicate]] = None,
                 formula_pre_conditions: Optional[str] = None,
                 formula_post_conditions: Optional[str] = None,
                 formula_invariants: Optional[str] = None,
                 full: bool = False):
        """``Action()`` is the Java no-arg constructor (``id`` stays None); with ``full=True``
        the seven-argument Java constructor is reproduced (``id`` = 0)."""
        self.action_name: Optional[str] = None
        self.params: List[Any] = []
        self.pre_conditions: List[Predicate] = []
        self.post_conditions: List[Predicate] = []
        self.invariants: List[Predicate] = []
        self.beliefs: Set[str] = set()
        self.formula_pre_conditions: str = ""
        self.formula_post_conditions: str = ""
        self.formula_invariants: str = ""
        self.id: Optional[int] = None
        if full:
            if params is not None:
                self.params.extend(params)
            if preconditions is not None:
                self.pre_conditions.extend(preconditions)
            if post_conditions is not None:
                self.post_conditions.extend(post_conditions)
            if invariants is not None:
                self.invariants.extend(invariants)
            if formula_pre_conditions is not None:
                self.formula_pre_conditions = formula_pre_conditions
            if formula_post_conditions is not None:
                self.formula_post_conditions = formula_post_conditions
            if formula_invariants is not None:
                self.formula_invariants = formula_invariants
            self.id = 0

    def clear(self) -> None:
        """Reset the action to the empty state (name, params, conditions, formulas, id=-1, beliefs)."""
        self.action_name = ""
        self.params.clear()
        self.pre_conditions.clear()
        self.post_conditions.clear()
        self.invariants.clear()
        self.formula_pre_conditions = ""
        self.formula_post_conditions = ""
        self.formula_invariants = ""
        self.id = -1
        self.beliefs.clear()

    def get_params(self) -> List[Any]:
        return self.params

    def set_params(self, params: Optional[List[Any]]) -> None:
        if params is not None:
            self.params.clear()
            self.params.extend(params)
        else:
            print("Error when try to set param for Action:")
            print("inserted Params is null.")

    def get_action_name(self) -> Optional[str]:
        return self.action_name

    def set_action_name(self, name: str) -> None:
        self.action_name = name

    def get_pre_conditions(self) -> List[Predicate]:
        return self.pre_conditions

    def get_invariants(self) -> List[Predicate]:
        return self.invariants

    def get_post_conditions(self) -> List[Predicate]:
        return self.post_conditions

    def set_pre_conditions(self, values: Optional[List[Predicate]]) -> None:
        self.pre_conditions.clear()
        if values is not None:
            self.pre_conditions.extend(values)

    def set_post_conditions(self, values: Optional[List[Predicate]]) -> None:
        self.post_conditions.clear()
        if values is not None:
            self.post_conditions.extend(values)

    def set_invariants(self, values: Optional[List[Predicate]]) -> None:
        self.invariants.clear()
        if values is not None:
            self.invariants.extend(values)

    def add_pre_condition(self, value: Predicate) -> None:
        self.pre_conditions.append(value)

    def add_post_condition(self, value: Predicate) -> None:
        self.post_conditions.append(value)

    def add_invariant(self, value: Predicate) -> None:
        self.invariants.append(value)

    def set_id(self, value: int) -> None:
        self.id = value

    def get_id(self) -> Optional[int]:
        return self.id

    def get_beliefs(self) -> Set[str]:
        return self.beliefs

    def set_beliefs(self, values: Optional[Set[str]]) -> None:
        self.beliefs.clear()
        if values is not None:
            self.beliefs.update(values)

    def copy_action(self, action: "Action") -> None:
        """Make this action a copy of ``action``. Java quirk kept: Formula_Pre_Conditions is not copied
        (Formula_Invariants is copied twice).
        """
        self.clear()
        self.action_name = action.action_name
        self.params.extend(action.params)
        self.pre_conditions.extend(action.pre_conditions)
        self.post_conditions.extend(action.post_conditions)
        self.invariants.extend(action.invariants)
        # Java copies Formula_Invariants twice and never Formula_Pre_Conditions:
        self.formula_post_conditions = action.formula_post_conditions
        self.formula_invariants = action.formula_invariants
        self.id = action.id
        self.beliefs.update(action.beliefs)

    def clone(self) -> "Action":
        action = Action()
        action.copy_action(self)
        return action

    def __repr__(self) -> str:
        name = "null" if self.action_name is None else self.action_name
        return (f"TAction[Name='{name}', Params={self.params}, "
                f"Pre_conditions_Count={len(self.pre_conditions)}, "
                f"Post_Conditions_Count={len(self.post_conditions)}, "
                f"Invariants_Count={len(self.invariants)}]")


class Option:
    """Java: TOption."""

    def __init__(self, plans: Optional[List[Action]] = None):
        self.plan_actions: List[Action] = []
        if plans is not None:
            self.plan_actions.extend(plans)
        self.id_current_action: int = 0
        self.satisfied_time: Optional[datetime] = None

    def clear(self) -> None:
        self.plan_actions.clear()
        self.id_current_action = 0

    def get_plan_actions(self) -> List[Action]:
        return self.plan_actions

    def set_plan_actions(self, plan_actions: List[Action]) -> None:
        self.plan_actions.clear()
        self.plan_actions.extend(plan_actions)

    def get_id_current_action(self) -> int:
        return self.id_current_action

    def next_id_current_action(self) -> None:
        self.id_current_action += 1

    def actions_completed(self) -> bool:
        return self.id_current_action >= len(self.plan_actions)

    def is_satisfied(self) -> bool:
        return self.id_current_action >= len(self.plan_actions)

    def get_satisfied_time(self) -> Optional[datetime]:
        return self.satisfied_time

    def set_satisfied_time(self, value: Optional[datetime]) -> None:
        self.satisfied_time = value

    def get_current_action(self) -> Optional[Action]:
        if self.id_current_action < 0 or self.id_current_action >= len(self.plan_actions):
            return None
        return self.plan_actions[self.id_current_action]

    def get_previous_action(self) -> Optional[Action]:
        if self.id_current_action == 0:
            return None
        return self.plan_actions[self.id_current_action]  # sic (Java)


class Intention:
    """Java: TIntention."""

    def __init__(self, name: Optional[str], desire: Any, selected_option_id: Optional[int]):
        self.name = name
        self.desire = desire
        self.selected_option_id: int = -1 if selected_option_id is None else selected_option_id

    def get_active_desire(self) -> Any:
        return self.desire

    def get_attentional_desire(self) -> Any:
        return self.desire

    def set_desire(self, desire: Any) -> None:
        self.desire = desire

    def get_selected_option_id(self) -> int:
        return self.selected_option_id

    def set_selected_option_id(self, value: int) -> None:
        self.selected_option_id = value

    def clear(self) -> None:
        self.desire = None
        self.selected_option_id = -1

    def set_name(self, name: str) -> None:
        self.name = name

    def get_name(self) -> Optional[str]:
        return self.name

    def get_selected_option(self) -> Option:
        return self.desire.get_list_options()[self.selected_option_id]

    def __repr__(self) -> str:
        return (f"TIntention[Name='{self.name}', Desire={self.desire}, "
                f"Seleted_Option_Id={self.selected_option_id}]")
