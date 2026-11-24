"""Enumerations.

Java: TType_Relationship, TType_Status_Desire, TType_Desire, TType_Temporal_Operator,
TType_Intention_Evaluated, TType_Update_Contract.

Member values are the exact Java constant names, so ``Enum(value)`` reproduces Java's
``valueOf``. Names that are Python keywords or constants get a trailing underscore
(``is`` -> ``is_``, ``None`` -> ``None_``).
"""
from enum import Enum


class TypeRelationship(Enum):
    """Relationship of a predicate (``subject relationship object``); the trailing underscore of ``is_`` avoids
    the Python keyword.
    """
    is_ = "is"                  # a is b
    minor = "minor"             # a < b
    major = "major"             # a > b
    equal = "equal"             # a == b
    minor_equal = "minor_equal"  # a <= b
    major_equal = "major_equal"  # a >= b
    is_not = "is_not"           # a != b
    is_in = "is_in"             # in/at a place/set
    is_out = "is_out"           # not in place/set
    is_between = "is_between"   # to develop
    when = "when"               # to develop


class TypeStatusDesire(Enum):
    """Status of an attentional desire: None, Active, Standing, Satisfied."""
    None_ = "None"
    Active = "Active"
    Standing = "Standing"
    Satisfied = "Satisfied"


class TypeDesire(Enum):
    """Origin/kind of a desire (endogenous practical, exogenous epistemic or practical)."""
    Endogenous_Practical_Desire = "Endogenous_Practical_Desire"
    Exogenous_Epistemic_Desire = "Exogenous_Epistemic_Desire"
    Exogenous_Practical_Desire = "Exogenous_Practical_Desire"


class TypeTemporalOperator(Enum):
    """Temporal operator of a desire's final state (the case study uses Finally)."""
    None_ = "None"
    Finally = "Finally"
    Globally = "Globally"
    Until = "Until"


class TypeIntentionEvaluated(Enum):
    """Evaluation state of an intention during execution."""
    Not_Determined = "Not_Determined"
    Not_to_Execute = "Not_to_Execute"
    To_Execute = "To_Execute"
    To_Delete = "To_Delete"
    Correct_Executed = "Correct_Executed"
    Full_Executed = "Full_Executed"
    Satisfied = "Satisfied"
    Not_Satisfied = "Not_Satisfied"


class TypeUpdateContract(Enum):
    """The kinds of update a component can subscribe to in the Global Workspace
    (``insert_for_update_contract``); each wakes the subscriber through its message handler.
    """
    All_Updates = "All_Updates"
    Updated_Predicates = "Updated_Predicates"
    Updated_Standing_Desires = "Updated_Standing_Desires"
    Updated_Beliefs = "Updated_Beliefs"
    Updated_Uninhibited_Data = "Updated_Uninhibited_Data"
    Updated_Active_Desires = "Updated_Active_Desires"
    Updated_Active_Desires_with_Options = "Updated_Active_Desires_with_Options"
    Updated_Selected_Intentions = "Updated_Selected_Intentions"
    Updated_Stimuli = "Updated_Stimuli"
    Updated_Thresholds = "Updated_Thresholds"
    Internal_Signals = "Internal_Signals"
    Internal_Signals_Abort_Option = "Internal_Signals_Abort_Option"
    Internal_Signals_Delete_Intention = "Internal_Signals_Delete_Intention"
    Internal_Signals_Satisfied_Intention = "Internal_Signals_Satisfied_Intention"
    Updated_Perceptions = "Updated_Perceptions"
    Updated_Satisfied_Desires = "Updated_Satisfied_Desires"
    Updated_Critical_Beliefs = "Updated_Critical_Beliefs"
    Updated_Preconditions = "Updated_Preconditions"
    Updated_Filtered_Stimuli = "Updated_Filtered_Stimuli"
    Updated_Action_to_Execute = "Updated_Action_to_Execute"
    Updated_Executed_Action = "Updated_Executed_Action"
