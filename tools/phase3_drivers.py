"""Python counterparts of the Java test harnesses (Sorter, Trie, Broadcast; not included).

Each ``run_*`` takes the lines of a script and returns the output lines, in exactly the
format of the Java tool, so the tests can diff them against the recorded Java output.
"""
from __future__ import annotations

import os
import sys
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from catalina.agent_thread import AgentBaseThread  # noqa: E402
from catalina.desires import GreenDesire, PracticalDesire, QualityDesire  # noqa: E402
from catalina.enums import TypeRelationship, TypeUpdateContract  # noqa: E402
from catalina.formula import PropositionalFormula, TemporalPropositionalFormula  # noqa: E402
from catalina.global_workspace import GlobalWorkspace  # noqa: E402
from catalina.model import Predicate  # noqa: E402
from catalina.plan import Action, Intention, Option  # noqa: E402
from catalina.plan_library import GlitterTrie  # noqa: E402
from catalina.sorters import BooleanExpressionSorter, SOPSorter  # noqa: E402


def esc(s: str) -> str:
    return (s.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
             .replace("\t", "\\t").replace("|", "\\p"))


def unesc(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            i += 1
            n = s[i]
            out.append({"n": "\n", "r": "\r", "t": "\t", "p": "|"}.get(n, n))
        else:
            out.append(c)
        i += 1
    return "".join(out)


# ---------------------------------------------------------------- sorters
def run_sorter(lines: List[str]) -> List[str]:
    out: List[str] = []
    for line in lines:
        expr = unesc(line)
        r = BooleanExpressionSorter.sort_expression(expr)
        out.append("|".join(["B", esc(r.get_full_expression()), str(len(r.get_product_list()))]
                            + [esc(p) for p in r.get_product_list()]))
        s = SOPSorter(expr)
        out.append("|".join(["S", esc(str(s)), str(s.get_product_count())]
                            + [esc(p) for p in s.get_all_products()]))
    return out


# ---------------------------------------------------------------- trie
def _val(spec: str):
    t, v = spec[0], spec[2:]
    return {"B": lambda: v.lower() == "true", "I": lambda: int(v), "D": lambda: float(v),
            "S": lambda: v, "N": lambda: None}[t]()


def _preds(spec: str) -> List[Predicate]:
    if spec == "":
        return []
    result = []
    for item in spec.split(";"):
        name, value = item.split("=", 1)
        result.append(Predicate(name, "me", TypeRelationship.is_, _val(value)))
    return result


def _desire(goal: str, greens: str, qualities: str) -> PracticalDesire:
    final_state = TemporalPropositionalFormula()
    final_state.set_formula(goal)
    g = [GreenDesire(p.get_name(), p, "T", 0.5, 0.5, 0.5, 0.5) for p in _preds(greens)]
    q = [QualityDesire(p.get_name(), p, "T", 0.5, 0.5, 0.5) for p in _preds(qualities)]
    return PracticalDesire("D", final_state, PropositionalFormula(), 0.5, 0.5, 0.5, g, q,
                           None, None, None, None, None, None, [], [])


def run_trie(lines: List[str]) -> List[str]:
    trie = GlitterTrie()
    out: List[str] = []
    for line in lines:
        f = line.split("\t")
        try:
            if f[0] == "PLAN":
                d = _desire(f[1], f[2], f[3])
                acts = []
                for i in range(int(f[5])):
                    a = Action()
                    a.set_action_name(f"{f[7]}_a{i}")
                    if i == 0:
                        a.set_pre_conditions(_preds(f[4]))
                    acts.append(a)
                d.set_list_options([Option(acts)])
                it = Intention("I", d, int(f[6]))
                out.append(f"PLAN {f[7]} -> {'true' if trie.create_plan(it) else 'false'}")
            else:
                d = _desire(f[1], f[2], f[3])
                r = trie.get_plans(d, _preds(f[4]))
                out.append("GET -> [" + ",".join(a.get_action_name() for a in r) + "]")
        except Exception:  # noqa: BLE001 - the Java tool prints EXC for any exception
            out.append(f"{f[0]} -> EXC")
    return out


# ---------------------------------------------------------------- broadcast
_DUMP_FLAGS = ("predicates", "beliefs", "uninhibited_data", "standing_desires", "active_desires",
               "active_desires_with_options", "stimuli", "selected_intentions", "thresholds",
               "internal_signals", "perceptions", "satisfied_desires", "important_beliefs",
               "preconditions", "filtered_stimuli", "action_to_execute", "executed_action")


class _Sub(AgentBaseThread):
    def __init__(self, name: str):
        super().__init__(None, name)

    def execute(self) -> None:
        pass

    def insert_in_list_update_contract(self) -> None:
        pass

    def _queue(self, label: str, messages) -> str:
        parts = []
        for m in messages:
            q = m.read_message()
            data = "[" + ", ".join(str(x) for x in q.get_object_fourth()) + "]"
            parts.append(f"({'true' if q.get_object_first() else 'false'},{q.get_object_second()},"
                         f"{q.get_object_third()},{data})")
        return f"{label}=[" + "".join(parts) + "]"

    def dump(self) -> str:
        h = self.message_handler
        flags = "".join(f + "," for f in _DUMP_FLAGS if h.read_value(f))
        return (f"{self.name}: flags={flags} "
                f"{self._queue('abort', h.read_internal_signals_abort_option_messages())} "
                f"{self._queue('delete', h.read_internal_signals_delete_intention_messages())} "
                f"{self._queue('satisfied', h.read_internal_signals_satisfied_intention_messages())}")

    def clear(self) -> None:
        h = self.message_handler
        for f in _DUMP_FLAGS:
            h.read_value_and_clear(f)
        h.read_and_clear_internal_signals_abort_option_messages()
        h.read_and_clear_internal_signals_delete_intention_messages()
        h.read_and_clear_internal_signals_satisfied_intention_messages()


def run_broadcast(lines: List[str]) -> List[str]:
    gw = GlobalWorkspace(None)
    subs = {}
    out: List[str] = []
    for line in lines:
        f = line.split("\t")
        if f[0] == "SUB":
            s = subs.setdefault(f[1], _Sub(f[1]))
            if f[2]:
                for c in f[2].split(","):
                    gw.insert_for_update_contract(TypeUpdateContract[c], s)
        elif f[0] == "SIGNAL":
            gw.broadcast_signal(TypeUpdateContract[f[1]])
        elif f[0] == "INTERNAL":
            data = f[3].split(",") if f[3] else []
            gw.broadcast_internal_signals_messages(TypeUpdateContract[f[1]], f[2], data)
        elif f[0] == "DUMP":
            out.append(f"-- counter={gw.contatore_di_broadcast}")
            out.extend(s.dump() for s in subs.values())
        elif f[0] == "CLEAR":
            for s in subs.values():
                s.clear()
    return out


# ---------------------------------------------------------------- maps
def run_maps(data_dir: str, epistemic_xml: str) -> List[str]:
    from catalina.maps import MapBeliefToSalienceStimuli, MapStimulusToEpistemicDesires
    out: List[str] = []
    m = MapBeliefToSalienceStimuli()
    m.load_mapped_epistemic_desires(data_dir)
    for k in sorted(m.get_mapped_stimuli()):
        out.append(f"@@ SAL {k} = {m.get_mapped_stimuli()[k]}")
    e = MapStimulusToEpistemicDesires()
    e.set_file_path(epistemic_xml)
    e.load_mapped_epistemic_desires()
    for k in sorted(e.get_mapped_epistemic_desires()):
        d = e.get_mapped_epistemic_desires()[k]
        out.append(f"@@ MAP {k} | {d} | formula={d.trigger_condition_formula} | "
                   f"trig={_jl(d.trigger_condition_names)} | beliefs={_jl(d.list_beliefs_for_reasoner)} | "
                   f"regions={_jl(d.list_regions_for_reasoner)}")
    return out


def _jl(items) -> str:
    return "[" + ", ".join(items) + "]"
