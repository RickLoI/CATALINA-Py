"""Update-message layer of the Global Workspace.

Java: TBase_Message, TBase_Message_Handler.

A ``BaseMessage`` is a boolean flag plus (sender, type, data) guarded by a lock. Every
executive function owns a ``BaseMessageHandler`` (its "mailbox"); the Global Workspace owns
another one and, in ``GlobalWorkspace.broadcast()``, moves the raised flags to the mailboxes
of the subscribers.

Java method names -> Python
---------------------------
Java has three methods per flag, with slightly irregular names (``Read_Updated_Beliefs``,
``Read_Value_Updated_Active_Desires``, ``Read_Value_Update_Filtered_Stimuli``...). Here they are
uniform and take the flag name:

    read_value(flag)            Java Read_*            (does not clear)
    read_value_and_clear(flag)  Java Read_Value_And_Clear_*
    write_value(flag)           Java Write_Value_*

``flag`` is one of ``FLAGS`` (names in snake_case without the "Updated_" prefix). Java's
``Unhinibited`` typo is written ``uninhibited`` here.

The three "internal signal" queues (abort option / delete intention / satisfied intention)
are lists of messages: ``add_internal_signal_*``, ``read_internal_signals_*``,
``read_and_clear_internal_signals_*``.

Kept from Java (observable behaviour)
-------------------------------------
* ``read_data()`` returns the data AND clears it (the name suggests otherwise).
* ``add_value_updated_internal_signals_*`` store the sender name also as message type.
* ``write_value`` resets sender, type and data (a pure flag).
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from .conscious_data import Quadruple
from .protected import ProtectedList

FLAGS = (
    "predicates", "beliefs", "uninhibited_data", "standing_desires", "active_desires",
    "active_desires_with_options", "stimuli", "selected_intentions", "thresholds",
    "internal_signals", "perceptions", "satisfied_desires", "important_beliefs",
    "preconditions", "filtered_stimuli", "action_to_execute", "executed_action",
)


class BaseMessage:
    """Java: TBase_Message."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.value: bool = False
        self.sender: str = ""
        self.message_type: str = ""
        self.data: List[Any] = []

    def read_value(self) -> bool:
        with self._lock:
            return self.value

    def read_sender(self) -> str:
        with self._lock:
            return self.sender

    def read_message_type(self) -> str:
        with self._lock:
            return self.message_type

    def read_data(self) -> List[Any]:
        """Returns the data and CLEARS it (Java behaviour)."""
        with self._lock:
            elements = list(self.data)
            self.data.clear()
            return elements

    def read_data_and_clean(self) -> List[Any]:
        with self._lock:
            elements = list(self.data)
            self.value = False
            self.message_type = ""
            self.sender = ""
            self.data.clear()
            return elements

    def read_value_and_clear(self) -> bool:
        with self._lock:
            result = self.value
            self.value = False
            self.message_type = ""
            self.sender = ""
            self.data.clear()
            return result

    def read_message(self) -> Quadruple:
        with self._lock:
            return Quadruple(self.value, self.sender, self.message_type, list(self.data))

    def read_and_clean_all_message(self) -> Quadruple:
        with self._lock:
            message = Quadruple(self.value, self.sender, self.message_type, list(self.data))
            self.value = False
            self.sender = ""
            self.message_type = ""
            self.data.clear()
            return message

    def write_internal_signal(self, sender: str, message_type: str, data: List[Any]) -> None:
        with self._lock:
            self.value = True
            self.sender = sender
            self.message_type = message_type
            self.data.clear()
            self.data.extend(data)

    def clean(self) -> None:
        with self._lock:
            self.value = False
            self.sender = ""
            self.message_type = ""
            self.data.clear()

    def write_value(self) -> None:
        with self._lock:
            self.value = True
            self.sender = ""
            self.message_type = ""
            self.data.clear()

    def modify_list(self, value: bool, sender: Any, message_type: str, data: List[Any],
                    action: Callable[[bool, Any, str, List[Any]], None]) -> None:
        with self._lock:
            action(value, sender, message_type, data)


class BaseMessageHandler:
    """Java: TBase_Message_Handler."""

    def __init__(self) -> None:
        self._messages: Dict[str, BaseMessage] = {flag: BaseMessage() for flag in FLAGS}
        self.internal_signals_abort_option_messages: ProtectedList = ProtectedList()
        self.internal_signals_delete_intention_messages: ProtectedList = ProtectedList()
        self.internal_signals_satisfied_intention_messages: ProtectedList = ProtectedList()

    # ---- flags
    def read_value(self, flag: str) -> bool:
        return self._messages[flag].read_value()

    def read_value_and_clear(self, flag: str) -> bool:
        return self._messages[flag].read_value_and_clear()

    def write_value(self, flag: str) -> None:
        self._messages[flag].write_value()

    def message(self, flag: str) -> BaseMessage:
        return self._messages[flag]

    # ---- internal-signal queues
    def read_internal_signals_abort_option_messages(self) -> List[BaseMessage]:
        return self.internal_signals_abort_option_messages.read()

    def read_internal_signals_delete_intention_messages(self) -> List[BaseMessage]:
        return self.internal_signals_delete_intention_messages.read()

    def read_internal_signals_satisfied_intention_messages(self) -> List[BaseMessage]:
        return self.internal_signals_satisfied_intention_messages.read()

    def read_and_clear_internal_signals_abort_option_messages(self) -> List[BaseMessage]:
        return self.internal_signals_abort_option_messages.read_and_clear()

    def read_and_clear_internal_signals_delete_intention_messages(self) -> List[BaseMessage]:
        return self.internal_signals_delete_intention_messages.read_and_clear()

    def read_and_clear_internal_signals_satisfied_intention_messages(self) -> List[BaseMessage]:
        return self.internal_signals_satisfied_intention_messages.read_and_clear()

    @staticmethod
    def _signal(sender_name: str, data: List[Any]) -> BaseMessage:
        signal = BaseMessage()
        signal.write_internal_signal(sender_name, sender_name, data)  # type = sender (Java)
        return signal

    def add_value_updated_internal_signals_abort_option_message(self, sender_name: str,
                                                                data: List[Any]) -> None:
        self.internal_signals_abort_option_messages.add(self._signal(sender_name, data))

    def add_value_updated_internal_signals_delete_intention_message(self, sender_name: str,
                                                                    data: List[Any]) -> None:
        self.internal_signals_delete_intention_messages.add(self._signal(sender_name, data))

    def add_value_updated_internal_signals_satisfied_intention_message(self, sender_name: str,
                                                                       data: List[Any]) -> None:
        self.internal_signals_satisfied_intention_messages.add(self._signal(sender_name, data))
