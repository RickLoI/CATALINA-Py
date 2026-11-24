"""Thread-safe containers.

Java: TGeneric_Protected_Object, TGeneric_Protected_List,
TGeneric_Auto_Named_and_Protected_List (plus the AtomicLong used by the latter).

Semantics kept from the Java original (they are observable):
* ``ProtectedList.add / add_all / set_list`` skip duplicates (identity/equality) and
  ``add_all`` drops ``None`` elements, *mutating the list passed by the caller*.
* ``AutoNamedProtectedList`` overrides ``add / add_all / set_list`` WITHOUT the
  duplicate check, and increments ``inc_number`` by the number of elements added.
* ``read()`` returns a copy.

Deviation: Java's ``add_all(None)`` raises NullPointerException; here it is a no-op.
Python's ``threading.RLock`` replaces ReentrantReadWriteLock (readers do not run
concurrently; irrelevant for correctness with the GIL).
"""
from __future__ import annotations

import threading
from typing import Callable, Generic, Iterable, List, Optional, TypeVar

T = TypeVar("T")


class AtomicLong:
    """Thread-safe counter (Java AtomicLong)."""
    def __init__(self, value: int = 0):
        self._value = value
        self._lock = threading.Lock()

    def increment_and_get(self) -> int:
        with self._lock:
            self._value += 1
            return self._value

    def add_and_get(self, delta: int) -> int:
        with self._lock:
            self._value += delta
            return self._value

    def get(self) -> int:
        with self._lock:
            return self._value


class ProtectedObject(Generic[T]):
    """Java: TGeneric_Protected_Object."""

    def __init__(self, initial_data: Optional[T] = None):
        self._data = initial_data
        self._lock = threading.RLock()

    def read(self) -> Optional[T]:
        with self._lock:
            return self._data

    def write(self, new_data: Optional[T]) -> None:
        with self._lock:
            self._data = new_data

    def read_and_clear(self, new_data: Optional[T]) -> Optional[T]:
        with self._lock:
            result = self._data
            self._data = new_data
            return result

    def read_with_action(self, action: Callable[[Optional[T]], None]) -> None:
        with self._lock:
            action(self._data)

    def write_with_action(self, action: Callable[[Optional[T]], None]) -> None:
        with self._lock:
            action(self._data)

    def update_and_get(self, update_function: Callable[[Optional[T]], Optional[T]]) -> Optional[T]:
        with self._lock:
            self._data = update_function(self._data)
            return self._data


class BooleanProtectedObject(ProtectedObject[bool]):
    """Java: TBoolean_Protected_Object."""

    def set_true(self) -> None:
        self.write(True)

    def set_false(self) -> None:
        self.write(False)

    def read_and_clear_false(self) -> bool:
        """Java: Read_And_Clear() (no argument): returns the old value and stores False."""
        return self.read_and_clear(False)


class DoubleProtectedObject(ProtectedObject[float]):
    """Java: TDouble_Protected_Object."""

    def increment_and_get(self) -> float:
        return self.update_and_get(lambda v: v + 1 if v is not None else 1)

    def add_and_get(self, value: float) -> float:
        return self.update_and_get(lambda v: v + value if v is not None else value)


class ProtectedList(Generic[T]):
    """Java: TGeneric_Protected_List."""

    def __init__(self, initial_list: Optional[Iterable[T]] = None):
        self._list: List[T] = list(initial_list) if initial_list is not None else []
        self._lock = threading.RLock()

    def add(self, element: Optional[T]) -> None:
        with self._lock:
            if element is not None and element not in self._list:
                self._list.append(element)

    def remove(self, element: Optional[T]) -> bool:
        """Remove the first occurrence of ``element``; False if it is None or absent."""
        with self._lock:
            if element is None:
                return False
            try:
                self._list.remove(element)
                return True
            except ValueError:
                return False

    def remove_all(self, elements: List[T]) -> bool:
        """Remove every element of ``elements`` from the list (None entries are dropped from the caller's list
        too, like Java); True if something was removed.
        """
        with self._lock:
            elements[:] = [e for e in elements if e is not None]  # mutates caller list, like Java
            changed = False
            keep = []
            for item in self._list:
                if item in elements:
                    changed = True
                else:
                    keep.append(item)
            self._list[:] = keep
            return changed

    def remove_at(self, index: int) -> Optional[T]:
        with self._lock:
            if 0 <= index < len(self._list):
                return self._list.pop(index)
            return None

    def remove_if(self, predicate: Callable[[T], bool]) -> bool:
        with self._lock:
            keep = [x for x in self._list if not predicate(x)]
            removed = len(keep) != len(self._list)
            self._list[:] = keep
            return removed

    def get(self, index: int) -> Optional[T]:
        with self._lock:
            if 0 <= index < len(self._list):
                return self._list[index]
            return None

    def size(self) -> int:
        with self._lock:
            return len(self._list)

    def read(self) -> List[T]:
        with self._lock:
            return list(self._list)

    def read_and_clear(self) -> List[T]:
        with self._lock:
            elements = list(self._list)
            self._list.clear()
            return elements

    def clear(self) -> None:
        with self._lock:
            self._list.clear()

    def add_all(self, elements: Optional[List[T]]) -> None:
        with self._lock:
            if elements is None:
                return
            elements[:] = [e for e in elements if e is not None]  # mutates caller list, like Java
            for element in elements:
                if element not in self._list:
                    self._list.append(element)

    def set_list(self, new_list: Optional[Iterable[T]]) -> None:
        with self._lock:
            self._list.clear()
            if new_list is not None:
                for element in new_list:
                    if element not in self._list:
                        self._list.append(element)

    def is_empty(self) -> bool:
        with self._lock:
            return not self._list

    def modify_list(self, action: Callable[[List[T]], None]) -> None:
        with self._lock:
            action(self._list)

    def for_each_snapshot(self, action: Callable[[List[T]], None]) -> None:
        with self._lock:
            action(list(self._list))

    def __repr__(self) -> str:
        return "ProtectedList[" + ", ".join(repr(x) for x in self.read()) + "]"


class AutoNamedProtectedList(ProtectedList[T]):
    """Java: TGeneric_Auto_Named_and_Protected_List (no duplicate check, counts insertions)."""

    def __init__(self, initial_list: Optional[Iterable[T]] = None):
        super().__init__(initial_list)
        self.inc_number = AtomicLong(0)

    def get_inc_number(self) -> int:
        return self.inc_number.get()

    def add(self, element: T) -> None:
        with self._lock:
            self._list.append(element)
            self.inc_number.increment_and_get()

    def add_all(self, elements: Optional[List[T]]) -> None:
        with self._lock:
            if elements:
                self._list.extend(elements)
                self.inc_number.add_and_get(len(elements))

    def set_list(self, new_list: Optional[Iterable[T]]) -> None:
        """Replace the content with ``new_list`` and add its length to the update counter."""
        with self._lock:
            self._list.clear()
            added = 0
            if new_list:
                new_list = list(new_list)
                self._list.extend(new_list)
                added = len(new_list)
            self.inc_number.add_and_get(added)
