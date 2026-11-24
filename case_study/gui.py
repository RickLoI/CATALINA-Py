"""Web GUI of the case study (replaces the Java Swing window).

    python -m case_study.gui [--port 8765] [--speed 1] [--no-browser]

A small stdlib HTTP server runs the headless ``AutonomousVehicleDemo`` and publishes its event log;
the page (``gui_page.html``) draws the map, animates the car from the ``car_move`` events, shows the
log and the Global Workspace messages, and has the buttons of the Java GUI (Start/Suspend/Resume
AVA, Send danger, Low fuel, answer to the traffic control) plus an accelerable simulated clock:
speed slider (0.5x-50x) and pause. No dependencies besides the standard library.

The simulated clock scales the waits of the agent and of the car; CPU work (e.g. the option
generation of the reasoner, ~2 s for thousands of paths) is not scaled, so above ~5x the agent
"thinks" proportionally slower in simulated time (see README).
"""
from __future__ import annotations

import argparse
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from catalina.clock import SimClock

from .demo import AutonomousVehicleDemo
from .map_panel import CAR_START_TOP_LEFT

HERE = os.path.dirname(os.path.abspath(__file__))
SHOWN_KINDS = {"log", "car_move", "gw_update", "gw_signal", "stimulus", "scenario"}


class Session:
    """One run of the demo; recreated by 'Reset'."""

    def __init__(self, speed: float = 1.0):
        self.lock = threading.Lock()
        self.speed = speed
        self.demo: Optional[AutonomousVehicleDemo] = None
        self.started = False
        self.suspended = False
        self.reset()

    def reset(self) -> None:
        with self.lock:
            if self.demo is not None:
                self.demo.end_simulation(join_timeout=1.0)
            self.demo = AutonomousVehicleDemo(clock=SimClock(self.speed)).start()
            self.started = False
            self.suspended = False

    def state(self, since: int) -> Dict[str, Any]:
        """Snapshot for the page: events since ``since``, simulated time, speed, pause/started flags and
        car/route/city.
        """
        demo = self.demo
        events = [{"seq": e.seq, "sim": e.sim, "kind": e.kind, "data": e.data}
                  for e in demo.event_log.events[since:] if e.kind in SHOWN_KINDS]
        last = demo.event_log.events[-1].seq + 1 if demo.event_log.events else 0
        panel = demo.map_panel
        return {"events": events, "next": last, "now": demo.clock.now(), "speed": demo.clock.speed,
                "paused": demo.clock.paused, "started": self.started, "suspended": self.suspended,
                "car": panel.car_xy, "car_size": panel.car_size, "route": demo.belief_value("BL_Position_Route"),
                "city": demo.belief_value("BL_Position_City")}

    def static(self) -> Dict[str, Any]:
        panel = self.demo.map_panel
        return {"stations": {str(c): xy for c, xy in panel.stations_coords.items()},
                "routes": {str(n): pts for n, pts in panel.ruotes_coords.items()},
                "car_size": panel.car_size, "car_start": panel.car_xy,
                "start_top_left": CAR_START_TOP_LEFT}

    def command(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a button/slider command (start, suspend, resume, danger, low_fuel, tcs, speed, pause,
        unpause, reset, save_log).
        """
        demo = self.demo
        if name == "start" and not self.started:
            self.started = True
            demo.start_av()
        elif name == "suspend":
            demo.suspend_av()
            demo.clock.pause()
            self.suspended = True
        elif name == "resume":
            demo.resume_av()
            demo.clock.resume()
            self.suspended = False
        elif name == "danger":
            demo.send_a_danger()
        elif name == "low_fuel":
            demo.send_low_fuel_signal()
        elif name == "tcs":
            demo.submit_tcs_response(str(payload.get("text", "")))
        elif name == "speed":
            self.speed = max(0.05, min(200.0, float(payload.get("speed", 1.0))))
            demo.clock.set_speed(self.speed)
        elif name == "pause":
            demo.clock.pause()
        elif name == "unpause":
            demo.clock.resume()
        elif name == "reset":
            self.reset()
        elif name == "save_log":
            path = str(payload.get("path") or "catalina_events.jsonl")
            demo.event_log.dump_jsonl(path)
            return {"saved": os.path.abspath(path)}
        return {"ok": True}


def make_handler(session: Session):
    """Build the HTTP request handler class bound to a ``Session``."""
    class Handler(BaseHTTPRequestHandler):
        """HTTP handler: serves the page, the images and the JSON API (GET /api/static, /api/state, POST
        /api/cmd/<name>).
        """
        def log_message(self, *args: Any) -> None:       # quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj: Any) -> None:
            self._send(200, json.dumps(obj, default=str).encode("utf-8"), "application/json")

        def do_GET(self) -> None:
            """Serve the page, the static map data, the state and the two images."""
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                with open(os.path.join(HERE, "gui_page.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            elif url.path == "/api/static":
                self._json(session.static())
            elif url.path == "/api/state":
                since = int(parse_qs(url.query).get("since", ["0"])[0])
                self._json(session.state(since))
            elif url.path in ("/img/map", "/img/car"):
                name, ctype = (("map.jpeg", "image/jpeg") if url.path == "/img/map" else ("auto.png", "image/png"))
                with open(os.path.join(HERE, "img", name), "rb") as f:
                    self._send(200, f.read(), ctype)
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self) -> None:
            """Run a command posted to /api/cmd/<name>."""
            url = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except ValueError:
                payload = {}
            if url.path.startswith("/api/cmd/"):
                self._json(session.command(url.path.rsplit("/", 1)[1], payload))
            else:
                self._send(404, b"not found", "text/plain")

    return Handler


def main(argv=None) -> None:
    """Command-line entry point: start the HTTP server (and the browser unless ``--no-browser``)."""
    parser = argparse.ArgumentParser(description="CATALINA case study - web GUI")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--speed", type=float, default=1.0, help="initial simulated clock speed")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    session = Session(args.speed)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(session))
    url = f"http://127.0.0.1:{args.port}/"
    print("CATALINA GUI at", url, "(Ctrl+C to quit)")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        session.demo.end_simulation(join_timeout=1.0)
        server.server_close()


if __name__ == "__main__":
    main()
