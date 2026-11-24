"""Core data model.

Java: TPredicate, TBelief, TStimulus, TPerception, TRegion, TDouble_Object.

Notes on behaviour kept from Java:
* ``Belief.clone()`` always returns a plain ``Belief`` (Java ``Clone()`` calls
  ``new TBelief(this)``): a cloned ``Stimulus`` loses its saliency and its class.
* The clone copies the predicate (new ``Predicate`` with ``predicate_id = None``,
  sharing subject/complement references) and links it to the clone.
* ``Predicate.get_object_complement()`` raises after ``clear()`` (Java: NullPointerException).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Union

from .enums import TypeRelationship
from .protected import ProtectedObject


class DoubleObject:
    """Java: TDouble_Object. Holds (type name, value text) of a not yet normalised reference."""

    def __init__(self, first: Any = None, second: Any = None):
        self.object_first = first
        self.object_second = second

    def get_object_first(self) -> Any:
        return self.object_first

    def set_object_first(self, value: Any) -> None:
        self.object_first = value

    def get_object_second(self) -> Any:
        return self.object_second

    def set_object_second(self, value: Any) -> None:
        self.object_second = value

    def __repr__(self) -> str:
        return f"DoubleObject[first={self.object_first}, second={self.object_second}]"


class Predicate:
    """Java: TPredicate."""

    def __init__(self, name: str, subject: Any, relationship: TypeRelationship, object_complement: Any):
        self.name: str = name
        self.predicate_id: Optional[int] = None
        self.subject: Any = subject
        self.relationship: TypeRelationship = relationship
        self.object_complement: Optional[ProtectedObject] = ProtectedObject(object_complement)
        self.linked_belief: Optional["Belief"] = None
        self.linked_belief_name: str = ""

    def clear(self) -> None:
        self.subject = None
        self.object_complement = None

    def get_subject(self) -> Any:
        return self.subject

    def set_subject(self, subject: Any) -> None:
        self.subject = subject

    def get_relationship(self) -> TypeRelationship:
        return self.relationship

    def get_object_complement(self) -> Any:
        return self.object_complement.read()  # AttributeError after clear(), like Java NPE

    def set_object_complement(self, value: Any) -> None:
        self.object_complement.write(value)

    def get_predicate_id(self) -> Optional[int]:
        return self.predicate_id

    def set_predicate_id(self, value: int) -> None:
        self.predicate_id = value

    def get_name(self) -> str:
        return self.name

    def set_linked_belief(self, belief: "Belief") -> None:
        self.linked_belief = belief
        self.linked_belief_name = belief.get_name()

    def set_linked_belief_name(self, value: str) -> None:
        self.linked_belief_name = value

    def get_linked_belief_name(self) -> str:
        return self.linked_belief_name

    def get_linked_belief(self) -> Optional["Belief"]:
        return self.linked_belief

    def __repr__(self) -> str:
        complement = self.object_complement.read() if self.object_complement is not None else "null"
        return (f"OID@{id(self)} Predicate[Name='{self.name}', Predicate_ID={self.predicate_id}, "
                f"Subject={self.subject}, Relationship={self.relationship}, "
                f"Object_Complement={complement}, Linked_Belief_Name='{self.linked_belief_name}']")


class Belief:
    """Java: TBelief. ``predicate`` may be a ``Predicate`` or the predicate's name (str)."""

    def __init__(self, name: str, predicate: Union[Predicate, str, None], truth: bool,
                 information_source: Any, time_stamp: Optional[datetime], type_belief: str):
        self.name: str = name
        self.belief_id: Optional[int] = None
        self.type_belief: str = type_belief
        self.truth: bool = bool(truth)
        self.time_stamp: Optional[datetime] = time_stamp
        self.information_source: Any = information_source
        if isinstance(predicate, Predicate):
            self.predicate: Optional[Predicate] = predicate
            self.predicate_name: str = predicate.get_name()
            predicate.set_linked_belief(self)
        else:
            self.predicate = None
            self.predicate_name = predicate

    # --- accessors (names as in Java) -------------------------------------------------
    def get_predicate(self) -> Optional[Predicate]:
        return self.predicate

    def is_truth(self) -> bool:
        return self.truth

    def get_truth(self) -> bool:
        return self.truth

    def set_truth(self, truth: bool) -> None:
        self.truth = bool(truth)

    def get_belief_id(self) -> Optional[int]:
        return self.belief_id

    def set_belief_id(self, value: int) -> None:
        self.belief_id = value

    def get_name(self) -> str:
        return self.name

    def set_name(self, value: str) -> str:
        self.name = value
        return value

    def get_type_belief(self) -> str:
        return self.type_belief

    def set_predicate(self, predicate: Predicate) -> None:
        self.predicate = predicate
        self.predicate_name = predicate.get_name()  # AttributeError if None, like Java NPE
        self.predicate.set_linked_belief(self)

    def get_predicate_name(self) -> str:
        return self.predicate_name

    def get_time_stamp(self) -> Optional[datetime]:
        return self.time_stamp

    def set_time_stamp(self, value: Optional[datetime]) -> None:
        self.time_stamp = value

    def get_information_source(self) -> Any:
        return self.information_source

    def set_information_source(self, value: Any) -> None:
        self.information_source = value

    def update_belief(self, predicate: Predicate, truth: bool) -> None:
        self.predicate = predicate
        self.truth = bool(truth)

    def clone(self) -> "Belief":
        """Deep copy of the belief and its predicate. Always returns a plain Belief."""
        copy = Belief.__new__(Belief)
        copy.name = self.name
        copy.belief_id = self.belief_id
        copy.type_belief = self.type_belief
        copy.truth = self.truth
        copy.time_stamp = self.time_stamp
        copy.predicate_name = self.predicate_name
        copy.information_source = self.information_source
        if self.predicate is not None:
            copy.predicate = Predicate(self.predicate.get_name(), self.predicate.get_subject(),
                                       self.predicate.get_relationship(),
                                       self.predicate.get_object_complement())
            copy.predicate.set_linked_belief(copy)
        else:
            copy.predicate = None
        return copy

    def __repr__(self) -> str:
        return (f"OID@{id(self)} Belief[ID={self.belief_id}, Name='{self.name}', "
                f"Type='{self.type_belief}', Predicate='{self.predicate_name}', "
                f"Truth={str(self.truth).lower()}, Time={self.time_stamp}, Source={self.information_source}]")


class Stimulus(Belief):
    """Java: TStimulus (a Belief with a saliency)."""

    def __init__(self, name: str, predicate: Union[Predicate, str, None], saliency: float, truth: bool,
                 information_source: Any, time_stamp: Optional[datetime], type_belief: str):
        super().__init__(name, predicate, truth, information_source, time_stamp, type_belief)
        self.saliency: float = saliency

    def get_saliency(self) -> float:
        return self.saliency

    def update_saliency(self, saliency: float) -> None:
        self.saliency = saliency

    def __repr__(self) -> str:
        return f"Stimulus[Saliency={self.saliency}] " + super().__repr__()


class Perception:
    """Java: TPerception."""

    def __init__(self, time: Optional[datetime], perceived_data: List[Any], source: str):
        self.time_stamp = time
        self.perceived_data: List[Any] = list(perceived_data)
        self.source = source

    def get_perceived_data(self) -> List[Any]:
        return self.perceived_data

    def get_source(self) -> str:
        return self.source

    def get_time_stamp(self) -> Optional[datetime]:
        return self.time_stamp


class Region:
    """Java: TRegion (abstract). Subclassed by the case study (routes)."""

    def __init__(self, name: Optional[str] = None):
        self.name: Optional[str] = name

    def get_name(self) -> Optional[str]:
        return self.name

    def set_name(self, value: str) -> None:
        self.name = value
