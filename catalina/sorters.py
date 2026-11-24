"""Boolean-expression sorters used to build canonical keys of the plan library.

Java: BooleanExpressionSorter (the one the plan library uses: products separated by ``+``,
literals by ``&``) and TSOPSorter (alternative ``|`` / ``&`` version, not used by the trie).

Java ``String.split`` / ``trim`` / ``compareTo`` semantics are reproduced:
* ``split(regex)`` drops trailing empty strings (and returns ``[s]`` when nothing matches);
* ``trim()`` removes every char <= U+0020 (Python ``strip()`` would also remove Unicode spaces);
* strings compare by UTF-16 code unit in Java, by code point here (same for the BMP).
"""
from __future__ import annotations

import re
from functools import cmp_to_key
from typing import List, Optional

_TRIM_CHARS = "".join(chr(i) for i in range(0x21))


def java_trim(s: str) -> str:
    return s.strip(_TRIM_CHARS)


def java_split_literal(s: str, sep: str) -> List[str]:
    parts = s.split(sep)
    if len(parts) == 1:
        return parts
    while parts and parts[-1] == "":
        parts.pop()
    return parts


def java_compare(a: str, b: str) -> int:
    """Java String.compareTo (sign is what matters)."""
    if a == b:
        return 0
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return ord(a[i]) - ord(b[i])
    return len(a) - len(b)


def _compare_ignore_case(a: str, b: str) -> int:
    """Java ``String.compareToIgnoreCase`` (UTF-16 char by char, upper then lower case)."""
    n = min(len(a), len(b))
    for i in range(n):
        c1, c2 = a[i], b[i]
        if c1 != c2:
            c1, c2 = c1.upper(), c2.upper()
            if c1 != c2:
                c1, c2 = c1.lower(), c2.lower()
                if c1 != c2:
                    return ord(c1) - ord(c2)
    return len(a) - len(b)


_NON_ALNUM = re.compile(r"[^a-zA-Z0-9]")


def _alphabetical_comparator(s1: str, s2: str) -> int:
    clean1 = _NON_ALNUM.sub("", s1)
    clean2 = _NON_ALNUM.sub("", s2)
    cmp = _compare_ignore_case(clean1, clean2)
    if cmp == 0:
        return java_compare(s1, s2)
    return cmp


class SortedResult:
    """Java: BooleanExpressionSorter.SortedResult."""

    def __init__(self, full_expression: str, product_list: List[str]):
        self.full_expression = full_expression
        self.product_list = product_list

    def get_full_expression(self) -> str:
        return self.full_expression

    def get_product_list(self) -> List[str]:
        return self.product_list


class BooleanExpressionSorter:
    """Canonical form of a sum-of-products expression ('+' = OR, '&' = AND): literals sorted inside each
    product, products sorted, ``!( ... )`` products kept whole. Used to index plans in the plan library.
    """
    OR_SYMBOL = "+"
    AND_SYMBOL = "&"

    @staticmethod
    def sort_expression(expression: Optional[str]) -> SortedResult:
        """Return the sorted expression and the list of its sorted products (empty for a blank expression).
        """
        if expression is None or java_trim(expression) == "":
            return SortedResult("", [])
        raw_products = java_split_literal(expression, BooleanExpressionSorter.OR_SYMBOL)
        processed: List[str] = []
        key = cmp_to_key(_alphabetical_comparator)
        for raw_prod in raw_products:
            raw_prod = java_trim(raw_prod)
            globally_negated = False
            if raw_prod.startswith("!(") and raw_prod.endswith(")"):
                globally_negated = True
                raw_prod = java_trim(raw_prod[2:len(raw_prod) - 1])
            literals = java_split_literal(raw_prod, BooleanExpressionSorter.AND_SYMBOL)
            literal_list = [java_trim(lit) for lit in literals]
            literal_list.sort(key=key)
            sorted_product = " & ".join(literal_list)
            if globally_negated:
                sorted_product = "!(" + sorted_product + ")"
            processed.append(sorted_product)
        processed.sort(key=key)
        return SortedResult(" + ".join(processed), processed)


class SOPSorter:
    """Java: TSOPSorter."""

    def __init__(self, expression: Optional[str]):
        self.sorted_product_list: List[str] = self._parse_and_sort(expression)

    def get_product(self, index: int) -> str:
        if index < 0 or index >= len(self.sorted_product_list):
            raise IndexError(f"Invalid index {index}. There are only "
                             f"{len(self.sorted_product_list)} products.")
        return self.sorted_product_list[index]

    def get_product_count(self) -> int:
        return len(self.sorted_product_list)

    def get_all_products(self) -> List[str]:
        return list(self.sorted_product_list)

    def __str__(self) -> str:
        return " | ".join(self.sorted_product_list)

    @staticmethod
    def _literal_compare(s1: str, s2: str) -> int:
        var1 = s1.replace("!", "")
        var2 = s2.replace("!", "")
        name_compare = java_compare(var1, var2)
        if name_compare != 0:
            return name_compare
        return len(s1) - len(s2)

    @staticmethod
    def _parse_and_sort(expression: Optional[str]) -> List[str]:
        """Split on '|', strip outer parentheses, sort the literals of each term and the distinct terms (Java
        compare order).
        """
        if expression is None or expression == "":
            return []
        terms = java_split_literal(expression, "|")
        processed: List[str] = []
        for term in terms:
            term = java_trim(term)
            if term.startswith("("):
                term = term[1:]
            if term.endswith(")"):
                term = term[:-1]
            literals = [java_trim(x) for x in java_split_literal(term, "&")]
            literals.sort(key=cmp_to_key(SOPSorter._literal_compare))
            processed.append(" & ".join(literals))
        distinct = list(dict.fromkeys(processed))
        distinct.sort(key=cmp_to_key(java_compare))
        return distinct
