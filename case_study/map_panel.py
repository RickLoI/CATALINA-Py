"""Headless model of the map panel (Java: TMap_Panel, the non-painting part).

Holds the pixel coordinates of stations and routes, the car position and the three
start/suspend/resume operations of the GUI buttons. ``Move_Car_Slowly`` does not block on a Swing
timer: it publishes a ``car_move`` event (so that a GUI can animate it) and waits ``seconds`` of
*clock* time, which is simulated time when the demo uses a ``SimClock``.

Java quirk not reproduced: the Swing animation updates the car with a compounding interpolation
(non-linear path, same end point); a view should interpolate linearly between ``frm`` and ``to``.
"""
from __future__ import annotations

import os
import struct
from typing import Any, Dict, List, Optional, Tuple

from .domain import TCity
from .map_data import ROUTES_COORDS, STATIONS_COORDS

Point = Tuple[int, int]

CAR_START_TOP_LEFT = (50, 50)       # Java: Positions.get(0) in Initialize_GUI
CAR_SCALE = 0.2                     # Java: Resize_Car(0.2)


def _png_size(path: str) -> Optional[Tuple[int, int]]:
    """Width and height of a PNG read from its header (None if unreadable)."""
    try:
        with open(path, "rb") as f:
            head = f.read(24)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])
    except OSError:
        pass
    return None


class MapPanelModel:
    """Headless model of the Java map panel: station and route pixel coordinates, the car position and the
    three button operations.
    """
    def __init__(self, demo: Any, car_image_path: Optional[str] = None):
        self.demo = demo
        self.stations_coords: Dict[TCity, Point] = {TCity[n]: xy for n, xy in STATIONS_COORDS.items()}
        self.ruotes_coords: Dict[int, List[Point]] = {n: list(pts) for n, pts in ROUTES_COORDS.items()}
        size = _png_size(car_image_path) if car_image_path and os.path.exists(car_image_path) else None
        self.car_size: Tuple[int, int] = ((int(size[0] * CAR_SCALE), int(size[1] * CAR_SCALE))
                                          if size else (0, 0))
        # Java keeps the top-left corner of the image; the model keeps the centre.
        self.car_xy: Point = (CAR_START_TOP_LEFT[0] + self.car_size[0] // 2,
                              CAR_START_TOP_LEFT[1] + self.car_size[1] // 2)

    # ---- Move_Car_Slowly
    def move_car_slowly(self, destination: Point, seconds: float, route: Optional[int] = None,
                        step: Optional[int] = None) -> None:
        demo = self.demo
        frm = self.car_xy
        demo.event_log.emit("car_move", frm=frm, to=destination, duration=seconds, route=route, step=step)
        demo.clock.sleep(seconds)
        self.car_xy = destination

    # ---- buttons "Start AVA", "Suspend AVA", "Resume AVA"
    def start_av(self) -> None:
        """Java 'Start AVA': start and resume the seven executives, broadcast once and set both thresholds to
        0.3.
        """
        agent = self.demo.agent
        started = [agent.get_desire_handler_component(), agent.get_attention_modulation_component(),
                   agent.get_executive_inhibition_function(), agent.get_executive_perception_function(),
                   agent.get_executive_memory_maintenance_function(), agent.get_executive_reasoner_function(),
                   agent.get_executive_switching_function()]
        for executive in started:
            executive.start()
        for executive in started:
            executive.resume()
        agent.get_global_workspace().broadcast_signal(None)
        agent.get_global_workspace().update_saliency_and_attention_thresholds(0.3, 0.3)

    def _all_eight(self) -> List[Any]:
        agent = self.demo.agent
        return [agent.get_attention_modulation_component(), agent.get_desire_handler_component(),
                agent.get_executive_switching_function(), agent.get_executive_inhibition_function(),
                agent.get_executive_reasoner_function(), agent.get_executive_perception_function(),
                agent.get_executive_memory_maintenance_function(),
                agent.get_executive_resource_allocation_function()]

    def suspend_av(self) -> None:
        for executive in self._all_eight():
            executive.suspend()

    def resume_av(self) -> None:
        for executive in self._all_eight():
            executive.resume()
