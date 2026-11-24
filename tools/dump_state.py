"""Dump the LongMemory state in the same line format as the Java dump program (not included).

Used for differential testing of the data model and XML loaders against the Java original:
    python tools/dump_state.py <Data dir> > py_dump.txt
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any, Iterable, List

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from catalina.desires import EpistemicDesire, PracticalDesire  # noqa: E402
from catalina.long_memory import LongMemory  # noqa: E402
from catalina.model import Belief, DoubleObject, Predicate, Stimulus  # noqa: E402


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("|", "\\p")


def jbool(b: bool) -> str:
    return "true" if b else "false"


def time_str(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}"


def V(x: Any) -> str:
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "Boolean:" + jbool(x)
    if isinstance(x, int):
        return "Integer:" + str(x)
    if isinstance(x, float):
        return "Double:" + repr(x)
    if isinstance(x, str):
        return "String:" + esc(x)
    if isinstance(x, datetime):
        return "Time:" + time_str(x)
    if isinstance(x, Belief):
        return "Belief:" + x.get_name()
    if isinstance(x, Predicate):
        return "Predicate:" + x.get_name()
    if isinstance(x, DoubleObject):
        return "DoubleObject:" + V(x.get_object_first()) + "/" + V(x.get_object_second())
    return "Obj:" + type(x).__name__


def L(items: Iterable[str]) -> str:
    return "[" + ",".join(esc(i) for i in items) + "]"


def SL(items: Iterable[str]) -> str:
    return L(sorted(items))


def BNS(beliefs: Iterable[Belief]) -> str:
    return SL(b.get_name() for b in beliefs)


def dump(lm: LongMemory) -> List[str]:
    out: List[str] = []
    for p in lm.predicates.read():
        out.append("PREDICATE|%s|%s|%s|%s|%s|%s" % (
            p.get_predicate_id(), esc(p.get_name()), V(p.get_subject()), p.get_relationship().value,
            V(p.get_object_complement()), esc(p.get_linked_belief_name())))
    for b in lm.get_all_beliefs():
        p = b.get_predicate()
        out.append("BELIEF|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s" % (
            b.get_belief_id(), esc(b.get_name()), b.get_type_belief(), esc(str(b.get_predicate_name())),
            "null" if p is None else p.get_name(),
            "null" if p is None or p.get_linked_belief() is None else p.get_linked_belief().get_name(),
            jbool(b.is_truth()), V(b.get_time_stamp()), V(b.get_information_source()),
            "Stimulus" if isinstance(b, Stimulus) else "Belief",
            repr(b.get_saliency()) if isinstance(b, Stimulus) else "-"))
    for g in lm.get_all_green_desires():
        out.append("GREEN|%s|%s|%s|%s|%r|%r|%r|%r|%s|%s" % (
            g.get_name(), g.get_type_green_standing_desire(), g.get_constraint_name(),
            "null" if g.get_constraint() is None else g.get_constraint().get_name(),
            g.get_saliency(), g.get_reward(), g.get_relax_preference(), g.get_fee(),
            g.get_status_desire().value, jbool(g.check_satisfation())))
    for q in lm.get_all_quality_desires():
        out.append("QUALITY|%s|%s|%s|%s|%r|%r|%r|%s|%s" % (
            q.get_name(), q.get_type_quality_goal(), q.get_constraint_name(),
            "null" if q.get_constraint() is None else q.get_constraint().get_name(),
            q.get_saliency(), q.get_reward(), q.get_relax_preference(),
            q.get_status_desire().value, jbool(q.check_satisfation())))
    for d in lm.get_all_attentional_desires():
        parts = ["PRACTICAL" if isinstance(d, PracticalDesire) else "EPISTEMIC", esc(d.get_name()),
                 repr(d.get_saliency()), repr(d.get_reward()), repr(d.get_relax_preference()),
                 d.get_status_desire().value, jbool(d.check_satisfation())]
        parts.append("green_names=" + L(d.get_list_green_standing_desire_name()))
        parts.append("green_objs=" + L(g.get_name() for g in d.get_list_green_standing_desire()))
        parts.append("quality_names=" + L(d.get_list_quality_standing_desire_name()))
        parts.append("quality_objs=" + L(q.get_name() for q in d.get_list_quality_standing_desire()))
        parts.append("beliefs_reasoner=" + SL(d.get_beliefs_name_for_reasoner()))
        parts.append("regions_reasoner=" + SL(d.get_regions_name_for_reasoner()))
        parts.append("options=%d" % len(d.get_list_options()))
        parts.append("intention=" + ("null" if d.get_related_intention() is None else "set"))
        if isinstance(d, EpistemicDesire):
            parts.append("belief_name=" + esc(d.get_belief_name()))
            parts.append("belief_obj=" + ("null" if d.get_belief() is None else d.get_belief().get_name()))
        else:
            fs = d.get_final_state()
            op = fs.get_temporal_operator()
            parts.append("trigger_names=" + L(d.get_trigger_condition_names()))
            parts.append("trigger_formula=" + esc(d.get_trigger_condition_formula()))
            parts.append("trigger_obj_formula=" + esc(d.get_trigger_condition().get_formula()))
            parts.append("trigger_obj_beliefs=" + BNS(d.get_trigger_condition().get_beliefs()))
            parts.append("final_names=" + L(d.get_final_state_names()))
            parts.append("final_formula=" + esc(d.get_final_state_formula()))
            parts.append("final_obj_beliefs=" + BNS(fs.get_beliefs()))
            parts.append("final_obj_formula=" + esc(fs.get_formula()))
            parts.append("final_op_type=" + op.get_type_temporal_operator().value)
            parts.append("final_op_start=" + V(op.get_start_time()))
            parts.append("final_op_end=" + V(op.get_end_time()))
            parts.append("finally_start=" + V(d.get_finally_start()))
            parts.append("finally_end=" + V(d.get_finally_end()))
            parts.append("global_start=" + V(d.get_global_start()))
            parts.append("global_end=" + V(d.get_global_end()))
            parts.append("until_end=" + V(d.get_until_end()))
        out.append("|".join(parts))
    for d in lm.get_inhibited_attentional_desires():
        out.append("INHIBITED|" + d.get_name())
    for b in lm.important_beliefs.read():
        out.append("IMPORTANT|" + b.get_name())
    out.append("COUNTS|predicates=%d|beliefs=%d|attentional=%d" % (
        lm.predicates.size(), len(lm.get_all_beliefs()), len(lm.get_all_attentional_desires())))
    return out


def main(argv: List[str]) -> int:
    data_dir = argv[1] if len(argv) > 1 else "."
    lm = LongMemory()
    lm.initialize(data_dir)
    sys.stdout.write("\n".join(dump(lm)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
