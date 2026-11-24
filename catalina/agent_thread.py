"""Base class of the executive functions: one real thread each.

Java: TAgent_Base_Thread. The loop is the Java one:

    wait while paused -> sleep 50 ms -> execute()

``Suspend()`` / ``Resume()`` pause and unpause the loop (a paused thread blocks on a condition
variable). Subclasses implement ``execute()`` (one iteration) and
``insert_in_list_update_contract()`` (subscribe to the Global Workspace update contracts); the
latter is called from the base constructor, as in Java, so subclasses must not rely on their
own attributes there (only ``self.agent`` is set).

Deviations (documented, both for experiments):
* ``LOOP_PERIOD_MS`` is a class attribute (Java hard-codes 50). Tests lower it.
* Threads are daemons, so a script ends when the main thread does (Java ends with System.exit).
* ``stop()`` is added: sets the continue flag to false and wakes the thread if paused.
"""
from __future__ import annotations

import sys
import threading
import time
import traceback
from abc import ABC, abstractmethod
from typing import Any

from .clock import REAL_CLOCK
from .messages import BaseMessageHandler


class AgentBaseThread(threading.Thread, ABC):
    """Base class of every executive function: one daemon thread with the Java loop (see the module docstring).

    Subclasses implement ``execute`` (one iteration) and ``insert_in_list_update_contract`` (which Global
    Workspace signals wake them up, through ``self.message_handler``).
    """
    LOOP_PERIOD_MS = 50

    def __init__(self, agent: Any, executive_function_name: str):
        threading.Thread.__init__(self, name=executive_function_name, daemon=True)
        self.agent = agent
        self.message_handler = BaseMessageHandler()
        self._continue_thread = True
        self._continue_lock = threading.RLock()
        self._initial_start_signal = threading.Event()
        self._pause_cond = threading.Condition(threading.RLock())
        self._is_paused = False
        self.insert_in_list_update_contract()

    @abstractmethod
    def execute(self) -> None:
        ...

    @abstractmethod
    def insert_in_list_update_contract(self) -> None:
        ...

    def run(self) -> None:
        """Thread body: wait while paused, wait ``LOOP_PERIOD_MS`` on the agent clock, run ``execute``; any
        exception is printed and ends the thread (as in Java).
        """
        try:
            self.is_in_pause()
            while self.read_continue_thread():
                self.is_in_pause()
                self.wait_a_time(self.LOOP_PERIOD_MS)
                self.execute()
            print("I exit from loop")
        except Exception as e:  # noqa: BLE001 - same catch-all as Java
            print(f"{self.name}: Interrupted while waiting or running.")
            print(f"Captured Error: {e}")
            traceback.print_exc(file=sys.stdout)

    def is_in_pause(self) -> None:
        with self._pause_cond:
            while self._is_paused:
                self._pause_cond.wait()

    def suspend(self) -> None:
        with self._pause_cond:
            self._is_paused = True

    def resume(self) -> None:
        with self._pause_cond:
            self._is_paused = False
            self._pause_cond.notify_all()

    def start_executive_function(self) -> None:
        self._initial_start_signal.set()

    def wait_a_time(self, time_ms: int) -> None:
        getattr(self.agent, "clock", REAL_CLOCK).sleep(time_ms / 1000.0)

    def read_continue_thread(self) -> bool:
        with self._continue_lock:
            return self._continue_thread

    def read_and_clean_continue_thread(self) -> bool:
        with self._continue_lock:
            result = self._continue_thread
            self._continue_thread = False
            return result

    def write_continue_thread(self) -> None:
        with self._continue_lock:
            self._continue_thread = True

    def stop(self) -> None:
        self.read_and_clean_continue_thread()
        self.resume()

    def get_agent(self) -> Any:
        return self.agent

    def set_continue(self, value: bool) -> None:  # empty in Java
        pass
