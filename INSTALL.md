# CATALINA (Python) - installation and usage

(Italian version: [INSTALL.it.md](INSTALL.it.md))

## Requirements
- Python 3.10 or later (developed and tested with 3.13). No external libraries: standard library only.
- A web browser (for the GUI). Java is not needed.

## Installation
1. Unpack the zip (or clone the repository) in any folder (the path may contain spaces).
2. Open a terminal in that folder (`catalina_py`). There is nothing to install.
3. Quick check: `python3 -c "import catalina, case_study; print('ok')"`
   (on Windows use `python` or `py` instead of `python3`).

## Running the case study
**GUI (recommended):** `python3 -m case_study.gui`, or `sh run_gui.sh` (macOS/Linux), or double-click `run_gui.bat` (Windows).
The browser opens at http://127.0.0.1:8765/. Press "Start AVA". Controls:
- Start / Suspend / Resume AVA, Reset
- Send a danger (closed route): then answer in the TCS field, first the type (0 unknown, 1 rocks, 2 accident), then the duration (1-100), each with "Send"
- Low fuel (fuel reserve)
- Simulated clock speed slider (0.1x-100x) and "Pause clock"

Options: `--port 9000`, `--speed 2`, `--no-browser`.

**Without the GUI (log on the terminal):**
`python3 tools/run_scenario.py 60 "never" 0` runs 60 simulated seconds with no stimuli.
Danger after entering route 115, TCS answers 0 and 30:
`python3 tools/run_scenario.py 80 "I enter Route: [115]" 1.5 1 0 30`
Fuel: as above with the environment variable `STIMULUS=low_fuel` (Windows PowerShell: `$env:STIMULUS="low_fuel"`).

**Experiments:** see `case_study/experiment.py` (variants, repetitions, CSV) and `case_study/scenario.py`.

## Using the GUI, step by step
1. Start the GUI and press **Start AVA**: the car starts moving; the log on the right shows "I enter Route: [n]" and "I'm arrived in <city>".
2. **Send a danger** while the car is on a route (not before, otherwise nothing happens): the car stops and the log shows
   "Why is the route closed?". Type `0`, `1` or `2` in the TCS field and press **Send**; then the duration (1-100, in 15-minute slots) and **Send**.
   The car turns back and replans.
3. **Low fuel**: the car goes to refuel in the nearest city and resumes.
4. The **Speed** slider changes the simulated clock speed; **Pause clock** stops it; **Suspend/Resume AVA** suspends/resumes the
   agent's executive functions; **Reset** starts over.

## Troubleshooting
- *Port 8765 is busy:* `python3 -m case_study.gui --port 9000`.
- *The browser does not open by itself:* open the address printed by the program (`http://127.0.0.1:8765/`).
- *"python3" not found (Windows):* use `py` or `python`.
- *`./run_gui.bat` gives "permission denied" on macOS/Linux:* the `.bat` file is for Windows; use `sh run_gui.sh`.
- *The car stays still after "Send a danger":* the danger must be sent while the car is on a route; the virtual camera sees it only once per run (as in the Java original).

## Developer documentation
`docs/DEVELOPER_GUIDE.md` (code structure, data flow, how to make variations and experiments, how to extend) and the docstrings
in every module/class. (Italian version: `docs/GUIDA_SVILUPPATORE.md`.)

## Tests
`python3 -I -m unittest discover -s tests -v` (a few seconds). See `tests/README.md`.

Optional: `pip install -e .` installs the `catalina` and `case_study` packages so they can be imported from anywhere.

## Notes
- Recommended speed 1x-3x: computation time does not scale with the simulated clock (see README.md).
- `Data/Critical_Beliefs.xml` is intentionally empty (confirmed by the author of the Java code); `Data/Beliefs.xml` is the updated version (fields `Confidence` and `Is_Stimulus`, ignored by the loader, since the logic does not use them).
