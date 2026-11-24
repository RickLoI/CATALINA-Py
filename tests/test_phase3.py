"""Phase 3 tests: message layer, sorters, plan library (trie), maps, Global Workspace.

Differential tests compare Python output with output recorded from the real Java classes
(see tests/README.md and tests/fixtures/*.expected). Run:
    python3 -I -m unittest discover -s tests -v
"""
import io
import os
import re
import sys
import threading
import time
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import phase3_drivers as drv  # noqa: E402
import gw_scenario  # noqa: E402
from catalina.agent_thread import AgentBaseThread  # noqa: E402
from catalina.desire_data import DesireData, PracticalDesireData  # noqa: E402
from catalina.enums import TypeUpdateContract as C  # noqa: E402
from catalina.global_workspace import GlobalWorkspace  # noqa: E402
from catalina.messages import BaseMessage, BaseMessageHandler  # noqa: E402
from catalina.model import Predicate  # noqa: E402
from catalina.enums import TypeRelationship  # noqa: E402
from catalina.plan import Action, Intention, Option  # noqa: E402
from catalina.plan_library import GlitterTrie, JavaNullPointerError  # noqa: E402
from catalina.memory_maintenance import (GlobalWorkspaceMemoryMaintenance,  # noqa: E402
                                         UpdateBeliefFunctionResult)

FIX = os.path.join(HERE, "fixtures")
DATA = os.path.join(ROOT, "case_study", "Data") + "/"


def lines(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read().split("\n")[:-1]


class DifferentialTests(unittest.TestCase):
    def test_sorters_match_java(self):
        got = drv.run_sorter(lines("sorter_cases.in"))
        want = lines("sorter_cases.expected")
        self.assertEqual(len(got), len(want))
        bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
        self.assertEqual(bad[:3], [])

    def test_trie_matches_java(self):
        got = drv.run_trie(lines("trie_script.in"))
        want = lines("trie_script.expected")
        self.assertEqual(got, want)
        self.assertGreater(sum(1 for w in want if w.startswith("GET -> [") and w != "GET -> []"), 20)
        self.assertGreater(sum(1 for w in want if w.endswith("EXC")), 5)

    @staticmethod
    def _normalise(out):
        """Java iterates subscribers in HashSet (identity-hash) order, Python in insertion order.
        Which subscriber receives the data of a forwarded internal signal is therefore arbitrary,
        so queues are compared as multisets over the subscribers of one DUMP; flags exactly."""
        blocks, cur = [], None
        for line in out:
            if line.startswith("-- counter"):
                cur = [line]
                blocks.append(cur)
            else:
                cur.append(line)
        res = []
        for b in blocks:
            res.append(b[0])
            flags, queues = [], {"abort": [], "delete": [], "satisfied": []}
            for s in b[1:]:
                m = re.match(r"(\w+): flags=(.*?) abort=\[(.*?)\] delete=\[(.*?)\] satisfied=\[(.*?)\]$", s)
                flags.append((m.group(1), m.group(2)))
                for key, grp in (("abort", 3), ("delete", 4), ("satisfied", 5)):
                    queues[key].extend(re.findall(r"\(.*?\]\)", m.group(grp)))
            res.append(str(flags))
            res.extend(str(sorted(queues[k])) for k in ("abort", "delete", "satisfied"))
        return res

    def test_broadcast_routing_matches_java(self):
        got = self._normalise(drv.run_broadcast(lines("broadcast_script.in")))
        want = self._normalise(lines("broadcast_script.expected"))
        self.assertEqual(got, want)

    def test_global_workspace_scenario_matches_java(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            gw_scenario.run(DATA)
        got = [l for l in buf.getvalue().split("\n") if re.match(r"(@@|Error when|Belief_Name)", l)]
        self.assertEqual(got, lines("gw_scenario.expected"))

    def test_maps_match_java(self):
        got = drv.run_maps(DATA, os.path.join(FIX, "Stimulus_2_Epistemic_Desires.xml"))
        self.assertEqual(got, lines("maps.expected"))


class MessageTests(unittest.TestCase):
    def test_flag_lifecycle(self):
        h = BaseMessageHandler()
        self.assertFalse(h.read_value("beliefs"))
        h.write_value("beliefs")
        self.assertTrue(h.read_value("beliefs"))
        self.assertTrue(h.read_value("beliefs"))             # reading does not clear
        self.assertTrue(h.read_value_and_clear("beliefs"))
        self.assertFalse(h.read_value("beliefs"))

    def test_read_data_clears(self):
        m = BaseMessage()
        m.write_internal_signal("s", "t", [1, 2])
        self.assertEqual(m.read_data(), [1, 2])
        self.assertEqual(m.read_data(), [])
        self.assertTrue(m.read_value())                      # the flag survives read_data

    def test_internal_signal_type_is_sender(self):
        h = BaseMessageHandler()
        h.add_value_updated_internal_signals_abort_option_message("who", ["x"])
        msg = h.read_internal_signals_abort_option_messages()[0]
        self.assertEqual((msg.read_sender(), msg.read_message_type()), ("who", "who"))


class PlanTests(unittest.TestCase):
    def test_clone_loses_precondition_formula(self):
        a = Action(preconditions=[], full=True, formula_pre_conditions="P", formula_post_conditions="Q",
                   formula_invariants="I")
        c = a.clone()
        self.assertEqual((c.formula_pre_conditions, c.formula_post_conditions, c.formula_invariants), ("", "Q", "I"))

    def test_intention_none_option_is_minus_one(self):
        self.assertEqual(Intention("n", None, None).get_selected_option_id(), -1)

    def test_trie_null_pointer_on_prefix_node(self):
        script = ["PLAN\tA\t\t\tP1=I:1\t1\t0\tx", "GET\tA\t\t\t"]
        self.assertEqual(drv.run_trie(script), ["PLAN x -> false", "GET -> EXC"])
        with self.assertRaises(JavaNullPointerError):
            t = GlitterTrie()
            t.root.add_node_goal("A")
            d = drv._desire("A", "", "")
            t.get_plans(d, [])

    def test_trie_distinguishes_boxed_types(self):
        script = ["PLAN\tA\t\t\tP=I:1\t1\t0\ta", "GET\tA\t\t\tP=I:1", "GET\tA\t\t\tP=D:1.0", "GET\tA\t\t\tP=B:true"]
        # Integer 1 matches; Double 1.0 and Boolean true are different keys in Java: no plan found
        self.assertEqual(drv.run_trie(script)[1:], ["GET -> [a_a0]", "GET -> []", "GET -> []"])


class ThreadTests(unittest.TestCase):
    class Worker(AgentBaseThread):
        LOOP_PERIOD_MS = 1

        def __init__(self, name, gw, contracts):
            self.gw = gw
            self.contracts = contracts
            self.hits = 0
            self.errors = []
            super().__init__(None, name)

        def insert_in_list_update_contract(self):
            pass

        def subscribe(self):
            for c in self.contracts:
                self.gw.insert_for_update_contract(c, self)

        def execute(self):
            if self.message_handler.read_value_and_clear("thresholds"):
                self.hits += 1

    def test_pause_resume_and_stop(self):
        gw = GlobalWorkspace(None)
        w = self.Worker("w", gw, [C.Updated_Thresholds])
        w.subscribe()
        w.suspend()
        w.start()
        gw.update_saliency_and_attention_thresholds(0.1, 0.2)
        time.sleep(0.05)
        self.assertEqual(w.hits, 0)                          # paused: nothing consumed
        w.resume()
        deadline = time.time() + 2
        while w.hits == 0 and time.time() < deadline:
            time.sleep(0.005)
        self.assertEqual(w.hits, 1)
        buf = io.StringIO()
        with redirect_stdout(buf):
            w.stop()
            w.join(2)
        self.assertFalse(w.is_alive())

    def test_concurrent_producers_and_consumers(self):
        gw = GlobalWorkspace(None)
        workers = [self.Worker(f"w{i}", gw, [C.Updated_Thresholds]) for i in range(4)]
        for w in workers:
            w.subscribe()
            w.start()

        def produce():
            for i in range(200):
                gw.update_saliency_and_attention_thresholds(i / 1000.0, 0.3)

        producers = [threading.Thread(target=produce) for _ in range(4)]
        for p in producers:
            p.start()
        for p in producers:
            p.join()
        time.sleep(0.1)
        buf = io.StringIO()
        with redirect_stdout(buf):
            for w in workers:
                w.stop()
                w.join(2)
        self.assertEqual(gw.contatore_di_broadcast, 800)
        for w in workers:
            self.assertGreater(w.hits, 0)
            self.assertLessEqual(w.hits, 800)
            self.assertFalse(w.is_alive())


class MemoryMaintenanceTests(unittest.TestCase):
    def test_set_stimuli_in_gw_runs_registered_function(self):
        from catalina.long_memory import LongMemory
        lm = LongMemory(None)
        lm.initialize(DATA)
        gw = GlobalWorkspace(gw_scenario._AgentStub(lm))
        gw.acquire_agent_components()
        gw.mark_as_active_desires([], [d for d in lm.get_all_attentional_desires()
                                       if d.get_name() == "Visit_Paris"])
        mm = GlobalWorkspaceMemoryMaintenance(None, gw)
        stimulus = next(b for b in lm.get_all_beliefs() if b.get_name() == "ST_Stimulus_Low_Fuel")

        def fn(stim, beliefs, recall):
            r = UpdateBeliefFunctionResult()
            r.set_result(True)
            r.set_beliefs_to_change({"BL_Fuel_Level": ["Object_Complement", 5]})
            return r

        mm.register_update_beliefs_function(stimulus.get_type_belief(), fn)
        before = gw.contatore_di_broadcast
        mm.set_stimuli_in_gw([stimulus])
        self.assertEqual(gw.get_map_uninhibited_beliefs()["BL_Fuel_Level"].get_predicate().get_object_complement(), 5)
        self.assertEqual(gw.get_stimuli(), [stimulus])
        self.assertGreater(gw.contatore_di_broadcast, before + 1)

    def test_desire_data_getters_empty_the_set(self):
        d = DesireData()
        d.set_beliefs(["a", "b"])
        self.assertEqual(d.get_beliefs(), ["a", "b"])
        self.assertEqual(d.get_beliefs(), [])


if __name__ == "__main__":
    unittest.main()
