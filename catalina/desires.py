"""Desires.

Java: TDesire, TGreen_Desire, TQuality_Desire, TAttentional_Desire, TEpistemic_Desire,
TPractical_Desire.

Constructors: Java has an "object" flavour (lists of already built objects) and a "names"
flavour (what the XML loader uses, resolved later by ``LongMemory.normalize_*``). Python has
one ``__init__`` per class taking either; see each docstring.

Behaviour kept from Java:
* Names flavour of ``AttentionalDesire`` stores ``list_green_desire_names`` and
  ``list_quality_desire_names`` BY REFERENCE (no copy); trigger names, reasoner beliefs and
  reasoner regions are copied.
* ``PracticalDesire`` sets ``until_start = global_end`` (typo in Java, kept; ``until_start``
  is never read).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from .enums import TypeStatusDesire
from .formula import PropositionalFormula, TemporalPropositionalFormula
from .model import Belief, Predicate
from .protected import ProtectedList


class Desire:
    """Java: TDesire."""

    def __init__(self, name: str, saliency: float, reward: float, relax_preference: float):
        self.name: str = name
        self.saliency: float = saliency
        self.reward: float = reward
        self.relax_preference: float = relax_preference
        self.checked: bool = False
        self.status_desire: TypeStatusDesire = TypeStatusDesire.Standing

    def get_saliency(self) -> float:
        return self.saliency

    def set_saliency(self, saliency: float) -> None:
        self.saliency = saliency

    def get_reward(self) -> float:
        return self.reward

    def set_reward(self, reward: float) -> None:
        self.reward = reward

    def get_relax_preference(self) -> float:
        return self.relax_preference

    def set_relax_preference(self, value: float) -> None:
        self.relax_preference = value

    def check_satisfation(self) -> bool:
        return self.checked

    def set_satisfation(self, value: bool) -> None:
        self.checked = value

    def get_name(self) -> str:
        return self.name

    def set_name(self, name: str) -> None:
        self.name = name

    def set_status_desire(self, value: TypeStatusDesire) -> None:
        self.status_desire = value

    def get_status_desire(self) -> TypeStatusDesire:
        return self.status_desire

    def __repr__(self) -> str:
        return (f"Desire[Name='{self.name}', Saliency={self.saliency}, Reward={self.reward}, "
                f"Relax_Preference={self.relax_preference}, Status={self.status_desire.value}]")


class _ConstraintDesire(Desire):
    """Common part of green and quality desires (constraint is a Predicate or its name)."""

    def __init__(self, name: str, constraint: Any, type_name: str, saliency: float, reward: float,
                 relax_preference: float):
        super().__init__(name, saliency, reward, relax_preference)
        self.type_name: str = type_name
        if isinstance(constraint, Predicate):
            self.constraint: Optional[Predicate] = constraint
            self.constraint_name: str = constraint.get_name()
        else:
            self.constraint = None
            self.constraint_name = constraint

    def set_constraint(self, constraint: Predicate) -> None:
        self.constraint = constraint
        self.constraint_name = constraint.get_name()

    def get_constraint_name(self) -> str:
        return self.constraint_name

    def get_constraint(self) -> Optional[Predicate]:
        return self.constraint


class GreenDesire(_ConstraintDesire):
    """Java: TGreen_Desire. ``constraint`` is a Predicate or a predicate name."""

    def __init__(self, name: str, constraint: Any, type_green_goal: str, saliency: float, reward: float,
                 relax_preference: float, fee: float):
        super().__init__(name, constraint, type_green_goal, saliency, reward, relax_preference)
        self.fee: float = fee

    def clear(self) -> None:
        self.constraint.clear()

    def get_type_green_standing_desire(self) -> str:
        return self.type_name

    def get_fee(self) -> float:
        return self.fee


class QualityDesire(_ConstraintDesire):
    """Java: TQuality_Desire. ``constraint`` is a Predicate or a predicate name."""

    def __init__(self, name: str, constraint: Any, type_quality_goal: str, saliency: float, reward: float,
                 relax_preference: float):
        super().__init__(name, constraint, type_quality_goal, saliency, reward, relax_preference)

    def get_type_quality_goal(self) -> str:
        return self.type_name


class AttentionalDesire(Desire):
    """Java: TAttentional_Desire.

    Either pass built objects (``trigger_condition``, ``green_desires``, ``quality_desires``) or
    names (``trigger_condition_formula``, ``trigger_condition_names``, ``green_desire_names``,
    ``quality_desire_names``), as the two Java constructors do.
    """

    def __init__(self, name: str, saliency: float, reward: float, relax_preference: float,
                 beliefs_reasoner: Optional[List[str]] = None,
                 regions_reasoner: Optional[List[str]] = None,
                 trigger_condition: Optional[PropositionalFormula] = None,
                 green_desires: Optional[List[GreenDesire]] = None,
                 quality_desires: Optional[List[QualityDesire]] = None,
                 trigger_condition_formula: Optional[str] = None,
                 trigger_condition_names: Optional[List[str]] = None,
                 green_desire_names: Optional[List[str]] = None,
                 quality_desire_names: Optional[List[str]] = None,
                 from_names: bool = False):
        super().__init__(name, saliency, reward, relax_preference)
        self.sum_for_attention_treshold: float = 0.15
        self.related_intention: Any = None
        self.list_options: ProtectedList = ProtectedList()
        if from_names:
            self.trigger_condition: PropositionalFormula = PropositionalFormula()
            self.trigger_condition_names: List[str] = list(trigger_condition_names)
            self.trigger_condition_formula: str = trigger_condition_formula
            self.green_standing_desires: List[GreenDesire] = []
            self.quality_desires: List[QualityDesire] = []
            self.list_green_desire_names: List[str] = green_desire_names      # by reference, like Java
            self.list_quality_desire_names: List[str] = quality_desire_names  # by reference, like Java
        else:
            self.trigger_condition = trigger_condition if trigger_condition is not None else PropositionalFormula()
            self.trigger_condition_names = [b.get_name() for b in self.trigger_condition.get_beliefs()]
            self.trigger_condition_formula = self.trigger_condition.get_formula()
            self.green_standing_desires = green_desires if green_desires is not None else []
            self.quality_desires = quality_desires if quality_desires is not None else []
            self.list_green_desire_names = [g.get_name() for g in self.green_standing_desires]
            self.list_quality_desire_names = [q.get_name() for q in self.quality_desires]
        self.beliefs_reasoner: List[str] = []   # Java HashSet<String>
        for n in (beliefs_reasoner or []):
            if n not in self.beliefs_reasoner:
                self.beliefs_reasoner.append(n)
        self.regions_reasoner: List[str] = []
        for n in (regions_reasoner or []):
            if n not in self.regions_reasoner:
                self.regions_reasoner.append(n)

    def clear(self) -> None:
        self.list_options.clear()
        self.related_intention = None
        self.green_standing_desires.clear()
        self.quality_desires.clear()
        self.list_green_desire_names.clear()
        self.list_quality_desire_names.clear()

    def get_list_green_standing_desire(self) -> List[GreenDesire]:
        return self.green_standing_desires

    def get_list_green_standing_desire_name(self) -> List[str]:
        return self.list_green_desire_names

    def set_list_green_standing_desire(self, values: List[GreenDesire]) -> None:
        values = list(values)  # Java: clear() then addAll(); protect against aliasing
        self.green_standing_desires.clear()
        self.green_standing_desires.extend(values)

    def get_list_quality_standing_desire(self) -> List[QualityDesire]:
        return self.quality_desires

    def get_list_quality_standing_desire_name(self) -> List[str]:
        return self.list_quality_desire_names

    def set_list_quality_standing_desire(self, values: List[QualityDesire]) -> None:
        values = list(values)
        self.quality_desires.clear()
        self.quality_desires.extend(values)

    def verify_precondition(self) -> bool:
        return True  # Java: Check_Precondition() always returns true

    def get_sum_for_attention_treshold(self) -> float:
        return self.sum_for_attention_treshold

    def get_related_intention(self) -> Any:
        return self.related_intention

    def set_related_intention(self, value: Any) -> None:
        self.related_intention = value

    def get_list_options(self) -> List[Any]:
        return self.list_options.read()

    def set_list_options(self, values: List[Any]) -> None:
        self.list_options.clear()
        self.list_options.add_all(values)

    def clear_options(self) -> None:
        self.list_options.clear()

    def get_beliefs_name_for_reasoner(self) -> List[str]:
        return list(self.beliefs_reasoner)

    def get_regions_name_for_reasoner(self) -> List[str]:
        return list(self.regions_reasoner)

    def set_beliefs_name_for_reasoner(self, names: List[str]) -> None:
        self.beliefs_reasoner = list(dict.fromkeys(names))

    def set_regions_name_for_reasoner(self, names: List[str]) -> None:
        self.regions_reasoner = list(dict.fromkeys(names))

    def __repr__(self) -> str:
        intention = "null" if self.related_intention is None else self.related_intention.get_name()
        return (f"AttentionalDesire[{super().__repr__()}Related_Intention='{intention}', "
                f"Options_Count={self.list_options.size()}, Green_Desires={self.list_green_desire_names}, "
                f"Quality_Desires={self.list_quality_desire_names}] ")


class EpistemicDesire(AttentionalDesire):
    """Java: TEpistemic_Desire.

    Names flavour (loader): ``EpistemicDesire.from_names(...)``.
    Object flavour: ``EpistemicDesire(name, belief, trigger_condition, ...)``.
    """

    def __init__(self, name: str, belief: Belief, trigger_condition: Optional[PropositionalFormula],
                 saliency: float, reward: float, relax_preference: float,
                 green_desires: Optional[List[GreenDesire]], quality_desires: Optional[List[QualityDesire]],
                 beliefs_reasoner: Optional[List[str]], regions_reasoner: Optional[List[str]] = None,
                 _names: Optional[dict] = None):
        if _names is None:
            super().__init__(name, saliency, reward, relax_preference, beliefs_reasoner, regions_reasoner,
                             trigger_condition=trigger_condition, green_desires=green_desires,
                             quality_desires=quality_desires)
            self.belief: Optional[Belief] = belief
            self.belief_name: str = belief.get_name()
        else:
            super().__init__(name, saliency, reward, relax_preference, beliefs_reasoner, regions_reasoner,
                             from_names=True, **_names)
            self.belief = None
            self.belief_name = belief  # here ``belief`` carries the belief name

    @classmethod
    def from_names(cls, name: str, belief_name: str, trigger_condition_formula: str,
                   trigger_condition_names: List[str], saliency: float, reward: float,
                   relax_preference: float, green_desire_names: List[str], quality_desire_names: List[str],
                   beliefs_reasoner: Optional[List[str]], regions_reasoner: Optional[List[str]] = None
                   ) -> "EpistemicDesire":
        """Build an epistemic desire from belief names only; the objects are resolved later against the long-
        term memory.
        """
        return cls(name, belief_name, None, saliency, reward, relax_preference, None, None,
                   beliefs_reasoner, regions_reasoner,
                   _names=dict(trigger_condition_formula=trigger_condition_formula,
                               trigger_condition_names=trigger_condition_names,
                               green_desire_names=green_desire_names,
                               quality_desire_names=quality_desire_names))

    def discover(self, belief_name: str) -> bool:
        return True  # Java: "TO DO DEVELOPMENT"

    def get_belief(self) -> Optional[Belief]:
        return self.belief

    def set_belief(self, belief: Belief) -> None:
        self.belief = belief
        self.belief_name = belief.get_name()

    def get_belief_name(self) -> str:
        return self.belief_name

    def __repr__(self) -> str:
        return f"EpistemicDesire[{super().__repr__()}Belief_Name='{self.belief_name}'] "


class PracticalDesire(AttentionalDesire):
    """Java: TPractical_Desire.

    Names flavour (loader): ``PracticalDesire.from_names(...)``.
    Object flavour: ``PracticalDesire(name, final_state, trigger_condition, ...)``.
    """

    def __init__(self, name: str, final_state: Optional[TemporalPropositionalFormula],
                 trigger_condition: Optional[PropositionalFormula],
                 saliency: float, reward: float, relax_preference: float,
                 green_desires: Optional[List[GreenDesire]], quality_desires: Optional[List[QualityDesire]],
                 finally_start: Optional[datetime], finally_end: Optional[datetime],
                 global_start: Optional[datetime], global_end: Optional[datetime],
                 until_start: Optional[datetime], until_end: Optional[datetime],
                 beliefs_reasoner: Optional[List[str]], regions_reasoner: Optional[List[str]] = None,
                 _names: Optional[dict] = None):
        if _names is None:
            super().__init__(name, saliency, reward, relax_preference, beliefs_reasoner, regions_reasoner,
                             trigger_condition=trigger_condition, green_desires=green_desires,
                             quality_desires=quality_desires)
            self.final_state: TemporalPropositionalFormula = final_state
            self.final_state_names: List[str] = [b.get_name() for b in final_state.get_beliefs()]
            self.final_state_formula: str = self.final_state.get_formula()
        else:
            super().__init__(name, saliency, reward, relax_preference, beliefs_reasoner, regions_reasoner,
                             from_names=True,
                             trigger_condition_formula=_names["trigger_condition_formula"],
                             trigger_condition_names=_names["trigger_condition_names"],
                             green_desire_names=_names["green_desire_names"],
                             quality_desire_names=_names["quality_desire_names"])
            self.final_state = TemporalPropositionalFormula()
            self.final_state.get_temporal_operator().set_start_time(finally_start)
            self.final_state.get_temporal_operator().set_end_time(finally_end)
            self.final_state_names = list(_names["final_state_names"])
            self.final_state_formula = _names["final_state_formula"]
        self.finally_start = finally_start
        self.finally_end = finally_end
        self.global_start = global_start
        self.global_end = global_end
        self.until_start = global_end   # Java typo kept (``Until_Start = global_End``)
        self.until_end = until_end

    @classmethod
    def from_names(cls, name: str, final_state_names: List[str], trigger_condition_names: List[str],
                   final_state_formula: str, trigger_condition_formula: str,
                   saliency: float, reward: float, relax_preference: float,
                   green_desire_names: List[str], quality_desire_names: List[str],
                   finally_start: Optional[datetime], finally_end: Optional[datetime],
                   global_start: Optional[datetime], global_end: Optional[datetime],
                   until_start: Optional[datetime], until_end: Optional[datetime],
                   beliefs_reasoner: Optional[List[str]], regions_reasoner: Optional[List[str]] = None
                   ) -> "PracticalDesire":
        """Build a practical desire from belief names and formulas only (and the three optional time
        intervals); the objects are resolved later against the long-term memory.
        """
        return cls(name, None, None, saliency, reward, relax_preference, None, None,
                   finally_start, finally_end, global_start, global_end, until_start, until_end,
                   beliefs_reasoner, regions_reasoner,
                   _names=dict(final_state_names=final_state_names, final_state_formula=final_state_formula,
                               trigger_condition_names=trigger_condition_names,
                               trigger_condition_formula=trigger_condition_formula,
                               green_desire_names=green_desire_names,
                               quality_desire_names=quality_desire_names))

    def get_trigger_condition(self) -> PropositionalFormula:
        return self.trigger_condition

    def get_trigger_condition_names(self) -> List[str]:
        return self.trigger_condition_names

    def get_trigger_condition_formula(self) -> str:
        return self.trigger_condition_formula

    def set_trigger_condition(self, trigger_condition: PropositionalFormula) -> None:
        """Copy the trigger condition formula and refresh ``trigger_condition_names`` from its beliefs."""
        if self.trigger_condition is None:
            self.trigger_condition = PropositionalFormula()
        self.trigger_condition.set_formula(trigger_condition.get_formula())
        self.trigger_condition.set_name(trigger_condition.get_name())
        self.trigger_condition.set_beliefs(trigger_condition.get_beliefs())
        self.trigger_condition_names.clear()
        for belief in trigger_condition.get_beliefs():
            self.trigger_condition_names.append(belief.get_name())
        self.trigger_condition_formula = self.trigger_condition.get_formula()

    def get_final_state(self) -> TemporalPropositionalFormula:
        return self.final_state

    def set_final_state(self, final_state: TemporalPropositionalFormula) -> None:
        """Copy the final state (operator, beliefs, formula, name) and refresh ``final_state_names`` from its
        beliefs.
        """
        if self.final_state is None:
            self.final_state = TemporalPropositionalFormula()
        self.final_state.set_temporal_operator(final_state.get_temporal_operator())
        self.final_state.set_beliefs(final_state.get_beliefs())
        self.final_state.set_formula(final_state.get_formula())
        self.final_state.set_name(final_state.get_name())
        self.final_state_names.clear()
        for belief in final_state.get_beliefs():
            self.final_state_names.append(belief.get_name())
        self.final_state_formula = final_state.get_formula()

    def get_final_state_names(self) -> List[str]:
        return self.final_state_names

    def get_final_state_formula(self) -> str:
        return self.final_state_formula

    def get_finally_start(self) -> Optional[datetime]:
        return self.finally_start

    def get_finally_end(self) -> Optional[datetime]:
        return self.finally_end

    def get_global_start(self) -> Optional[datetime]:
        return self.global_start

    def get_global_end(self) -> Optional[datetime]:
        return self.global_end

    def get_until_end(self) -> Optional[datetime]:
        return self.until_end
