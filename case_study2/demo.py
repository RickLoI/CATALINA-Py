from __future__ import annotations

import os
import threading
from typing import Any, Iterable, List, Optional

# Catalina related
from catalina.agent import Agent
from catalina.clock import RealClock


HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "Data")


class WindTurbineDemo:
    def __init__(self, data_dir: Optional[str] = None,
                 clock: Optional[Any] = None,
                 scripted_answers: Optional[Iterable[str]] = None,
                 echo: bool = False):
        self.data = data_dir or DATA
        self.clock = clock if clock is not None else RealClock()
        self.agent: Optional[Agent] = None
        self.long_mem = None
