"""Boolean and temporal propositional formulas.

Java: TBoolean_Expression_Evaluetor, TPropositional_Formula, TTemporal_Propositional_Formula,
TTemporal_Operator.

Evaluator: same operator-precedence algorithm as Java ('!' > '^' > '&' = '|', left to right,
parentheses). Kept quirks: '&' and '|' have equal precedence; a double negation such as
"!!A" raises ValueError, exactly as the Java stack machine does ("Missing operand").

Intentional deviations (documented because Java behaviour is a bug in these cases):
* Java keeps the variable map in a *static* field shared by every evaluator and thread, and
  substitutes values with ``String.replaceAll(name, "T"/"F")`` in HashMap order, so a variable
  whose name is contained in another name (``BL_Low_Fuel_Level`` / ``BL_Low_Fuel_Level_Warning``)
  can corrupt the expression. Here variables are per-instance and identifiers are tokenised
  whole. In the case study the only caller (TEndogenous_Desire_Promotion) clears and refills the
  variables right before each evaluation and uses single-belief formulas, so results are identical.
* An identifier without a value raises ValueError (Java ends in an obscure parsing error).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional, Set

from .enums import TypeTemporalOperator
from .model import Belief

_IDENT = re.compile(r"[A-Za-z0-9_.]+")
_PRECEDENCE = {"!": 3, "^": 2, "&": 1, "|": 1, "(": 0}


class BooleanExpressionEvaluator:
    """Java: TBoolean_Expression_Evaluetor (spelling of the Java class kept in the alias below)."""

    def __init__(self) -> None:
        self.variables: Dict[str, bool] = {}

    def set_variable(self, variable: str, value: bool) -> None:
        self.variables[variable] = bool(value)

    def clear(self) -> None:
        self.variables.clear()

    def evaluate(self, expression: str) -> bool:
        return evaluate_expression(expression, self.variables)

    def __repr__(self) -> str:
        return f"BooleanExpressionEvaluator[CurrentVariables={self.variables}]"


def _substitute(expression: str, variables: Dict[str, bool]) -> str:
    """Replace every variable of ``expression`` by T/F using ``variables``; the constants T and F stay; an
    unknown variable raises ValueError.
    """
    def repl(match: "re.Match[str]") -> str:
        token = match.group(0)
        if token not in variables and token in ("T", "F"):
            return token  # literal constant
        if token not in variables:
            raise ValueError(f"Boolean expression: no value for variable '{token}'")
        return "T" if variables[token] else "F"

    return _IDENT.sub(repl, expression)


def _apply_top_operator(operands: List[bool], operators: List[str]) -> None:
    """Pop one operator (``!``, ``&``, ``|``, ``^``) and apply it to the top operand(s) of the evaluation
    stack.
    """
    op = operators.pop()
    if op == "!":
        if not operands:
            raise ValueError("Missing operand for operator '!'")
        operands.append(not operands.pop())
        return
    if len(operands) < 2:
        raise ValueError(f"Missing operands for the operator {op}")
    b = operands.pop()
    a = operands.pop()
    if op == "&":
        operands.append(a and b)
    elif op == "|":
        operands.append(a or b)
    elif op == "^":
        operands.append(a != b)
    else:
        raise ValueError(f"Invalid operator: {op}")


def evaluate_expression(expression: str, variables: Dict[str, bool]) -> bool:
    """Evaluate ``expression`` ('&', '|', '^', '!', parentheses) with the given variable values."""
    expression = re.sub(r"\s+", "", _substitute(expression, variables))
    operands: List[bool] = []
    operators: List[str] = []
    for ch in expression:
        if ch in ("T", "F"):
            operands.append(ch == "T")
        elif ch == "(":
            operators.append(ch)
        elif ch == ")":
            while operators and operators[-1] != "(":
                _apply_top_operator(operands, operators)
            if not operators:
                raise ValueError("Unbalanced parentheses")  # Java: EmptyStackException
            operators.pop()
        else:
            while operators and _PRECEDENCE.get(ch, -1) <= _PRECEDENCE.get(operators[-1], -1):
                _apply_top_operator(operands, operators)
            operators.append(ch)
    while operators:
        _apply_top_operator(operands, operators)
    if len(operands) != 1:
        raise ValueError("In Boolean Expression Evaluator, Wrong expression.")
    return operands.pop()


class PropositionalFormula:
    """Java: TPropositional_Formula."""

    def __init__(self) -> None:
        self.beliefs: List[Belief] = []          # Java HashSet; insertion order kept (deterministic)
        self.beliefs_names: List[str] = []       # Java HashSet<String>
        self.formula: str = ""
        self.propositional_formula_name: str = ""

    def get_beliefs(self) -> List[Belief]:
        return list(self.beliefs)

    def get_beliefs_names(self) -> List[str]:
        return list(self.beliefs_names)

    def set_name(self, name: str) -> None:
        self.propositional_formula_name = name

    def get_name(self) -> str:
        return self.propositional_formula_name

    def set_beliefs(self, beliefs: List[Belief]) -> None:
        """Store the beliefs without duplicates (keeping order) and rebuild the list of their distinct names.
        """
        self.beliefs = []
        for b in beliefs:
            if b not in self.beliefs:
                self.beliefs.append(b)
        self.beliefs_names = []
        for b in self.beliefs:
            if b.get_name() not in self.beliefs_names:
                self.beliefs_names.append(b.get_name())

    def set_beliefs_by_name(self, beliefs_name: List[str], beliefs: List[Belief]) -> None:
        names = set(beliefs_name)
        self.beliefs = []
        for b in beliefs:
            if b.get_name() in names and b not in self.beliefs:
                self.beliefs.append(b)

    def set_beliefs_names(self, beliefs_names: List[str]) -> None:
        self.beliefs_names = []
        for n in beliefs_names:
            if n not in self.beliefs_names:
                self.beliefs_names.append(n)

    def get_formula(self) -> str:
        return self.formula

    def set_formula(self, formula: str) -> None:
        self.formula = formula

    def verify_formula(self) -> bool:
        evaluator = BooleanExpressionEvaluator()
        for belief in self.beliefs:
            evaluator.set_variable(belief.get_name(), belief.is_truth())
        return evaluator.evaluate(self.formula)

    def __repr__(self) -> str:
        return (f"PropositionalFormula[Name='{self.propositional_formula_name}', "
                f"Formula='{self.formula}', Beliefs_Names={{{', '.join(self.beliefs_names)}}}]")


class TemporalOperator:
    """Java: TTemporal_Operator."""

    def __init__(self) -> None:
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.type_temporal_operator: TypeTemporalOperator = TypeTemporalOperator.None_
        self.temporal_operator_name: str = ""

    def get_start_time(self) -> Optional[datetime]:
        return self.start_time

    def get_end_time(self) -> Optional[datetime]:
        return self.end_time

    def set_start_time(self, value: Optional[datetime]) -> None:
        self.start_time = value

    def set_end_time(self, value: Optional[datetime]) -> None:
        self.end_time = value

    def get_type_temporal_operator(self) -> TypeTemporalOperator:
        return self.type_temporal_operator

    def set_type_temporal_operator(self, value: TypeTemporalOperator) -> None:
        self.type_temporal_operator = value

    def get_temporal_operator_name(self) -> str:
        return self.temporal_operator_name

    def set_temporal_operator_name(self, value: str) -> None:
        self.temporal_operator_name = value


class TemporalPropositionalFormula(PropositionalFormula):
    """Java: TTemporal_Propositional_Formula."""

    def __init__(self) -> None:
        super().__init__()
        self.temporal_operator = TemporalOperator()
        self.list_temporal_propositional_formula: List["TemporalPropositionalFormula"] = []
        self.list_temporal_propositional_formula_names: List[str] = []

    def get_temporal_operator(self) -> TemporalOperator:
        return self.temporal_operator

    def set_temporal_operator(self, value: TemporalOperator) -> None:
        # Java copies the four fields into the existing operator instance
        self.temporal_operator.set_start_time(value.get_start_time())
        self.temporal_operator.set_end_time(value.get_end_time())
        self.temporal_operator.set_type_temporal_operator(value.get_type_temporal_operator())
        self.temporal_operator.set_temporal_operator_name(value.get_temporal_operator_name())

    def get_list_temporal_propositional_formula_names(self) -> List[str]:
        return list(self.list_temporal_propositional_formula_names)

    def set_list_temporal_propositional_formula_names(self, names: Optional[List[str]]) -> None:
        self.list_temporal_propositional_formula_names.clear()
        if names is not None:
            self.list_temporal_propositional_formula_names.extend(names)

    def get_list_temporal_propositional_formula(self) -> List["TemporalPropositionalFormula"]:
        return list(self.list_temporal_propositional_formula)

    def set_list_temporal_propositional_formula(self, elements: List["TemporalPropositionalFormula"]) -> None:
        self.list_temporal_propositional_formula.clear()
        self.list_temporal_propositional_formula.extend(elements)
