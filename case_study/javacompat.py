"""Small helpers that reproduce Java collection behaviour the case study depends on."""
from __future__ import annotations

from typing import Dict, Hashable, Iterable, List, TypeVar

K = TypeVar("K", bound=Hashable)


class ConcurrentModificationError(RuntimeError):
    """Java ``ConcurrentModificationException``."""


def hashmap_key_order(keys: Iterable[int]) -> List[int]:
    """Iteration order of a Java ``HashMap<Integer, ?>`` holding ``keys`` (given in insertion order).

    Bucket index = ``(h ^ (h >>> 16)) & (capacity - 1)`` with ``h`` the Integer value; capacity 16
    doubled while size > 0.75 * capacity; same-bucket keys stay in insertion order. (The capacity
    of a real map never shrinks after removals; here it is derived from the current size.)
    """
    keys = list(keys)
    capacity = 16
    while len(keys) > capacity * 0.75:
        capacity *= 2

    def bucket(k: int) -> int:
        h = k & 0xFFFFFFFF
        return (h ^ (h >> 16)) & (capacity - 1)

    return sorted(keys, key=bucket)     # sorted() is stable


def remove_while_iterating(mapping: Dict[int, object], should_remove) -> bool:
    """Iterate ``mapping`` in Java ``HashMap`` order calling ``should_remove(key)``; removes matches.

    Java's fail-fast iterator throws ``ConcurrentModificationException`` on the ``next()`` that
    follows a removal if the iteration has not ended. Returns True when something was removed.
    """
    order = hashmap_key_order(mapping.keys())
    removed = False
    for position, key in enumerate(order):
        if removed:
            raise ConcurrentModificationError("java.util.ConcurrentModificationException")
        if should_remove(key):
            del mapping[key]
            removed = True
    return removed
