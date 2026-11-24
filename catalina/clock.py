"""Clocks.

The Java code uses real time everywhere: ``Thread.sleep`` in the executive loops and a Swing
``Timer`` in ``Move_Car_Slowly``. The Python port routes every wait through a *clock* object so
that an experiment can run faster (or slower) than real time without changing the behaviour of
the agent relative to the environment.

* ``RealClock``: plain ``time.sleep`` (speed 1, what Java does).
* ``SimClock``: a simulated clock with an adjustable *speed factor* (``speed=10`` means that
  10 simulated seconds pass in 1 real second) and pause/resume. ``sleep(s)`` blocks the calling
  thread until ``s`` simulated seconds have elapsed; changing the speed or pausing while threads
  sleep is honoured within ``POLL_REAL_S``.

Both clocks expose ``now()`` (seconds since the clock start; simulated seconds for ``SimClock``)
and ``sleep(seconds)``. The agent threads use ``sleep`` for their 50 ms loop period and the case
study uses it for the time a car step takes, so that at any speed the 50 ms of "agent thinking
period" and the 1 s of "one movement step" keep the Java ratio.

Each ``sleep`` yields the CPU for at least ``MIN_REAL_YIELD_S`` of real time, so that very high
speeds do not turn the executive loops into busy loops that starve the other threads.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

MIN_REAL_YIELD_S = 0.001
POLL_REAL_S = 0.05


class RealClock:
    """Wall clock; ``sleep`` is ``time.sleep``."""

    speed = 1.0

    def __init__(self) -> None:
        self._t0 = time.monotonic()

    def now(self) -> float:
        return time.monotonic() - self._t0

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)

    def stop(self) -> None:
        pass

    @property
    def stopped(self) -> bool:
        return False


REAL_CLOCK = RealClock()


class SimClock:
    """Simulated clock with adjustable speed (``speed`` simulated seconds per real second), pause and stop.

    All waits of the agent go through ``sleep``; ``now`` is the simulated time in seconds. Speed and pause
    can be changed while threads are sleeping: they re-evaluate their remaining time at least every
    ``POLL_REAL_S``.
    """
    def __init__(self, speed: float = 1.0) -> None:
        if speed <= 0:
            raise ValueError("speed must be > 0")
        self._cond = threading.Condition(threading.Lock())
        self._speed = float(speed)
        self._paused = False
        self._stopped = False
        self._base_sim = 0.0               # simulated seconds at ``_base_real``
        self._base_real = time.monotonic()

    # ---- reading
    def _now_locked(self) -> float:
        if self._paused:
            return self._base_sim
        return self._base_sim + (time.monotonic() - self._base_real) * self._speed

    def now(self) -> float:
        with self._cond:
            return self._now_locked()

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def stopped(self) -> bool:
        return self._stopped

    # ---- control
    def _rebase_locked(self) -> None:
        self._base_sim = self._now_locked()
        self._base_real = time.monotonic()

    def set_speed(self, speed: float) -> None:
        if speed <= 0:
            raise ValueError("speed must be > 0")
        with self._cond:
            self._rebase_locked()
            self._speed = float(speed)
            self._cond.notify_all()

    def pause(self) -> None:
        with self._cond:
            if not self._paused:
                self._rebase_locked()
                self._paused = True
                self._cond.notify_all()

    def resume(self) -> None:
        with self._cond:
            if self._paused:
                self._paused = False
                self._base_real = time.monotonic()
                self._cond.notify_all()

    def stop(self) -> None:
        """Wake every sleeping thread and make every later ``sleep`` return at once."""
        with self._cond:
            self._stopped = True
            self._cond.notify_all()

    # ---- waiting
    def sleep(self, seconds: float, interruptible: Optional[threading.Event] = None) -> None:
        """Block for ``seconds`` of *simulated* time (returns at once if the clock is stopped or
        ``interruptible`` is set).

        While paused it keeps waiting without consuming simulated time.
        """
        if seconds <= 0:
            return
        with self._cond:
            target = self._now_locked() + seconds
            first = True
            while not self._stopped:
                if interruptible is not None and interruptible.is_set():
                    return
                if self._paused:
                    self._cond.wait(POLL_REAL_S)
                    continue
                remaining = target - self._now_locked()
                if remaining <= 0 and not first:
                    return
                real_wait = max(remaining / self._speed, 0.0) if remaining > 0 else 0.0
                self._cond.wait(min(max(real_wait, MIN_REAL_YIELD_S), POLL_REAL_S))
                first = False
                if self._target_reached(target):
                    return

    def _target_reached(self, target: float) -> bool:
        return (not self._paused) and self._now_locked() >= target
