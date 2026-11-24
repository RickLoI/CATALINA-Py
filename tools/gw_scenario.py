"""Python counterpart of a Java test harness (not included): drives the Global Workspace through a fixed
scenario on the real case-study data and prints its state after every step.

    python tools/gw_scenario.py <Data dir>
"""
from __future__ import annotations

import os
import sys
from typing import Any, Iterable, List

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from catalina.desires import EpistemicDesire  # noqa: E402
from catalina.global_workspace import GlobalWorkspace  # noqa: E402
from catalina.long_memory import LongMemory  # noqa: E402
from catalina.memory_maintenance import LongTermMemoryMaintenance  # noqa: E402
from catalina.plan import Intention  # noqa: E402


class _MemoryMaintenanceStub:
    """Stands for TExecutive_Memory_Maintenance_Function (a thread, Phase 4)."""

    def __init__(self, long_memory: LongMemory):
        self.lt = LongTermMemoryMaintenance(self, long_memory)

    def get_lt_memory_maintenance(self):
        return self.lt


class _AgentStub:
    def __init__(self, long_memory: LongMemory):
        self.mm = _MemoryMaintenanceStub(long_memory)

    def get_executive_memory_maintenance_function(self):
        return self.mm

    def __getattr__(self, name):
        if name.startswith("get_"):
            return lambda: None
        raise AttributeError(name)


def jstr(x: Any) -> str:
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    return str(x)


def names(items: Iterable[str]) -> str:
    return "[" + ", ".join(sorted(items)) + "]"


def run(data_dir: str) -> List[str]:
    out: List[str] = []

    def P(s: str) -> None:
        print("@@ " + s)

    lm = LongMemory(None)
    lm.initialize(data_dir)
    gw = GlobalWorkspace(_AgentStub(lm))
    gw.acquire_agent_components()

    def dnames(c): return names(d.get_name() + ":" + d.get_status_desire().value for d in c)
    def plain(c): return names(d.get_name() for d in c)
    def bnames(c): return names(b.get_name() for b in c)

    def dump(label: str) -> None:
        P("== " + label)
        t = gw.get_saliency_and_attention_thresholds()
        P(f"thr={t.get_object_first()},{t.get_object_second()}")
        P(f"counter={gw.contatore_di_broadcast}")
        P("uninh_desires=" + dnames(gw.get_unhinibited_desires()))
        P("uninh_active=" + plain(gw.get_unhinibited_active_desires()))
        P("uninh_beliefs=" + bnames(gw.get_uninhibited_beliefs()))
        P("map_beliefs=" + names(gw.get_map_uninhibited_beliefs().keys()))
        P("precond=" + bnames(gw.get_preconditions()))
        P("uninh_regions=" + names(r.get_name() for r in gw.get_uninhibited_regions()))
        P("important=" + bnames(gw.get_important_beliefs()))
        parts = []
        for i in gw.get_selected_intentions():
            d = i.get_active_desire()
            parts.append(f"{jstr(i.get_name())}->{'null' if d is None else d.get_name()}#{i.get_selected_option_id()}")
        P("intentions=[" + ", ".join(parts) + "]")
        P("ltm_all=" + dnames(gw.get_all_attentional_desires_from_mm()))
        P("ltm_inhibited=" + plain(gw.get_inhibited_attentional_desires_from_lt()))
        P("ltm_satisfied=" + plain(gw.get_satisfied_attentional_desires_from_ltm()))
        P("ltm_inh_beliefs=" + bnames(gw.get_inhibited_beliefs_from_mm()))
        rl = sorted(f"{d.get_name()}->{d.get_related_intention().get_name()}"
                    for d in gw.get_all_attentional_desires_from_mm() if d.get_related_intention() is not None)
        P("related=[" + ", ".join(rl) + "]")

    def desire(name: str):
        for d in gw.get_all_attentional_desires_from_mm():
            if d.get_name() == name:
                return d
        raise RuntimeError("no desire " + name)

    def belief(name: str):
        return gw.get_all_map_beliefs_from_mm()[name]

    def belief_value(name: str) -> None:
        b = gw.get_map_uninhibited_beliefs()[name]
        P(f"belief {name}: subject={jstr(b.get_predicate().get_subject())} "
          f"complement={jstr(b.get_predicate().get_object_complement())} truth={jstr(b.is_truth())}")

    dump("init")
    P("attentional=" + plain(gw.get_attentional_desires()))
    P("epistemic=" + plain(gw.get_all_epistemic_desires()))
    P("practical=" + plain(gw.get_all_practical_desires()))
    P("practical_from_ltm=" + plain(gw.get_all_practical_desires_from_ltm()))
    dump("after lazy fill")

    gw.update_saliency_and_attention_thresholds(0.45, 0.65)
    dump("thresholds")

    d_a = desire("Visit_Frankfurt")
    d_b = desire("Visit_Paris")
    epi = None
    for d in gw.get_all_attentional_desires_from_mm():
        if isinstance(d, EpistemicDesire):
            epi = d
    gw.mark_as_active_desires([], [d_a, d_b, epi])
    dump("activated")
    P("active_practical=" + plain(gw.get_active_practical_desires()))

    gw.update_uninhibited_conscious_beliefs({
        "BL_Fuel_Level": ["Object_Complement", 42],
        "BL_Destination_Paris": ["Subject", "X"],
        "BL_NoSuch": ["Object_Complement", 1]})
    belief_value("BL_Fuel_Level")
    belief_value("BL_Destination_Paris")
    dump("beliefs updated")

    i1 = Intention(None, d_a, 0)
    i2 = Intention("Named", d_b, 0)
    gw.add_intentions([i1, i2])
    d_a.set_related_intention(i1)
    d_b.set_related_intention(i2)
    dump("intentions added")
    gw.add_intention(Intention(None, d_a, -1))
    dump("intention added")
    gw.set_selected_intentions([i2, Intention("", epi, None)])
    dump("selected set")

    gw.mark_as_standing_desires([d_a])
    dump("standing")
    gw.mark_as_satisfied_desires([d_b])
    dump("satisfied")

    P("recal=" + names(gw.recal_beliefs({"BL_Position_City", "BL_Map", "BL_NoSuch"}).keys()))
    dump("recal")

    pre = list(gw.get_selected_beliefs_from_ltm({"BL_Current_Time", "BL_Danger_on_the_Route"}).values())
    bel = list(gw.get_selected_beliefs_from_ltm({"BL_Fuel_Level", "BL_Map"}).values())
    gw.set_uninhibited_conscious_data(pre, bel, [d_a], [])
    dump("uninhibited data set")

    gw.set_important_beliefs([belief("BL_Fuel_Level")])
    gw.update_uninhibited_conscious_beliefs({"BL_Fuel_Level": ["Object_Complement", 7]})
    belief_value("BL_Fuel_Level")
    dump("important updated")

    gw.add_uninhibited_preconditions({belief("BL_Position_Route")})
    gw.add_uninhibited_preconditions(set())
    gw.add_uninhibited_preconditions(None)
    dump("preconditions added")

    gw.set_inhibited_conscious_data([belief("BL_Map")], [d_b], [])
    dump("inhibited set")

    gw.set_uninhibited_beliefs([belief("BL_Map"), belief("BL_Fuel_Level")])
    dump("uninhibited beliefs set")
    gw.set_beliefs([belief("BL_Map")])
    P("ltm_beliefs=" + bnames(gw.get_all_beliefs_from_mm()))
    dump("beliefs set in ltm")
    return out


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "case_study/Data/")
