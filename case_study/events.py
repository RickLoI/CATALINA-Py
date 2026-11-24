"""Structured event log (replaces the Swing ``Log_Memo`` and the "Global Workspace" window).

Every observable thing the case study does is appended here as an ``Event``:

========== =====================================================================================
kind       data
========== =====================================================================================
log        ``text`` (what Java appended to ``Log_Memo``), ``color`` (the unused Java colour code)
car_move   ``frm`` / ``to`` pixel centres, ``duration`` (simulated seconds), ``route``, ``step``
gw_update  summary printed by ``GlobalWorkspace_CallBack`` (after each GW information update)
gw_signal  summary printed by ``General_CallBack`` (after each broadcast signal)
stimulus   a scenario stimulus injected through a (virtual) button: ``name``
scenario   start / end markers of a run
========== =====================================================================================

``seq`` is a global order, ``sim`` the clock time (simulated seconds), ``wall`` the wall clock.
Subscribers are called synchronously under the log lock, so they must be cheap (the GUI only
enqueues). Text lines of the Java log are ``[e.data['text'] for e in log.of_kind('log')]``.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional


@dataclass
class Event:
    """One observable thing: global order ``seq``, simulated time ``sim``, wall time, emitting thread, ``kind``
    and a ``data`` dict (see the table above).
    """
    seq: int
    sim: float
    wall: float
    thread: str
    kind: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({"seq": self.seq, "sim": round(self.sim, 6), "wall": round(self.wall, 6),
                           "thread": self.thread, "kind": self.kind, "data": self.data},
                          default=str, ensure_ascii=False)


class EventLog:
    """Thread-safe, append-only list of events with synchronous subscribers; the GUI and the
    experiment metrics all read it.
    """
    def __init__(self, clock: Any = None, echo: bool = False):
        self.clock = clock
        self.echo = echo
        self._lock = threading.Lock()
        self._events: List[Event] = []
        self._subscribers: List[Callable[[Event], None]] = []
        self._wall0 = time.time()

    def set_clock(self, clock: Any) -> None:
        self.clock = clock

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        with self._lock:
            self._subscribers.append(callback)

    def emit(self, kind: str, **data: Any) -> Event:
        """Append an event (``kind`` and keyword data), call the subscribers and, with ``echo``, print log
        lines to stdout; returns the event.
        """
        with self._lock:
            sim = self.clock.now() if self.clock is not None else 0.0
            event = Event(len(self._events), sim, time.time() - self._wall0,
                          threading.current_thread().name, kind, data)
            self._events.append(event)
            for callback in self._subscribers:
                callback(event)
        if self.echo and kind == "log":
            print(data.get("text", ""), flush=True)
        return event

    # ---- reading
    @property
    def events(self) -> List[Event]:
        with self._lock:
            return list(self._events)

    def of_kind(self, *kinds: str) -> List[Event]:
        return [e for e in self.events if e.kind in kinds]

    def text_lines(self) -> List[str]:
        """The lines of the Java ``Log_Memo`` (one entry per ``Print`` call)."""
        return [e.data["text"] for e in self.of_kind("log")]

    def as_text(self) -> str:
        """Same content as ``Log_Memo.getText()`` in Java."""
        return "".join(t + "\n" for t in self.text_lines())

    def dump_jsonl(self, path: str, kinds: Optional[Iterable[str]] = None) -> None:
        wanted = set(kinds) if kinds is not None else None
        with open(path, "w", encoding="utf-8") as f:
            for e in self.events:
                if wanted is None or e.kind in wanted:
                    f.write(e.to_json() + "\n")
