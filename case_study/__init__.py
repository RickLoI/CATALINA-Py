"""Autonomous-vehicle case study (Java: ``Case Study Journal 001``).

Python port of the case study built on top of the ``catalina`` package. The modules mirror the
Java classes (see each module docstring); the Swing GUI is replaced by

* a headless view model (``map_panel.MapPanelModel``) + a structured event log (``events``), and
* an optional Tk GUI (``gui``) that only *reads* the event log,

and real time by a clock (``catalina.clock``) whose speed can be raised for experiments.
"""
