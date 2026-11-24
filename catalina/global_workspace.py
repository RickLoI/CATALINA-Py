"""The Global Workspace (Baars): the shared, "conscious" blackboard of the agent.

Java: TGlobal_Workspace.

What it holds: thresholds (saliency, attention), stimuli, uninhibited beliefs/desires/regions
and pre-conditions, intentions, the plan library. What it does: (1) stores/serves those lists
under locks, (2) ``broadcast_signal(contract)`` raises the matching flag in its own mailbox and
``broadcast()`` copies every raised flag to the mailbox of each executive function subscribed
to that contract (``insert_for_update_contract``).

Concurrency: every executive function is a real thread (``AgentBaseThread``) and calls the
methods of this class concurrently. The four Java ReentrantReadWriteLocks are replaced by
re-entrant mutexes; the locking order is the Java one.

Java quirks kept on purpose (all observable, none fixed)
--------------------------------------------------------
* ``broadcast_signal(Updated_Satisfied_Desires)`` raises the PERCEPTIONS flag (copy/paste in
  Java): ``Updated_Satisfied_Desires`` subscribers are never notified by it.
* ``broadcast_signal`` has no case for ``Updated_Preconditions`` and the ``Internal_Signals_*``
  contracts: only the callback runs and ``broadcast()`` is called.
* In ``broadcast()`` the delete/satisfied-intention messages are forwarded with
  ``read_sender()`` then ``read_data_and_clean()``: the first subscriber gets sender and data,
  the following ones get an empty sender and no data.
* ``add_uninhibited_conscious_data`` / ``remove_uninhibited_conscious_data`` rebuild the
  name->belief and name->region maps from the arguments only, not from the whole lists.
* ``get_attentional_desires`` fills the list from the Long Memory the first time it is empty.
* ``get_active_practical_desires`` returns every practical desire of the uninhibited list,
  whatever its status.

Deviations: ``contatore_di_broadcast`` is incremented under a lock (Java: racy ``++``);
subscriber sets keep insertion order (Java HashSet order is arbitrary).
"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional

from .conscious_data import ConsciousData
from .desire_data import DesireData
from .desires import AttentionalDesire, EpistemicDesire, PracticalDesire
from .enums import TypeStatusDesire, TypeUpdateContract
from .messages import BaseMessageHandler
from .model import Belief, DoubleObject, Region, Stimulus
from .plan import Intention
from .plan_library import GlitterTrie
from .protected import (AutoNamedProtectedList, BooleanProtectedObject, DoubleProtectedObject,
                        ProtectedList)

C = TypeUpdateContract

# Contract -> flag raised in the Global Workspace mailbox by broadcast_signal (Java switch).
_SIGNAL_FLAG = {
    C.Updated_Predicates: "predicates",
    C.Updated_Standing_Desires: "standing_desires",
    C.Updated_Beliefs: "beliefs",
    C.Updated_Uninhibited_Data: "uninhibited_data",
    C.Updated_Active_Desires: "active_desires",
    C.Updated_Active_Desires_with_Options: "active_desires_with_options",
    C.Updated_Selected_Intentions: "selected_intentions",
    C.Updated_Stimuli: "stimuli",
    C.Updated_Thresholds: "thresholds",
    C.Internal_Signals: "internal_signals",
    C.Updated_Perceptions: "perceptions",
    C.Updated_Satisfied_Desires: "perceptions",          # sic (Java copy/paste)
    C.Updated_Critical_Beliefs: "important_beliefs",
    C.Updated_Filtered_Stimuli: "filtered_stimuli",
    C.Updated_Action_to_Execute: "action_to_execute",
    C.Updated_Executed_Action: "executed_action",
}

# (mailbox flag, contract) in the order checked by Java's broadcast(). The two internal-signal
# queues are handled separately, between "satisfied_desires" and "important_beliefs".
_BROADCAST_FLAGS_BEFORE_QUEUES = (
    ("predicates", C.Updated_Predicates),
    ("standing_desires", C.Updated_Standing_Desires),
    ("beliefs", C.Updated_Beliefs),
    ("uninhibited_data", C.Updated_Uninhibited_Data),
    ("active_desires", C.Updated_Active_Desires),
    ("active_desires_with_options", C.Updated_Active_Desires_with_Options),
    ("selected_intentions", C.Updated_Selected_Intentions),
    ("stimuli", C.Updated_Stimuli),
    ("filtered_stimuli", C.Updated_Filtered_Stimuli),
    ("action_to_execute", C.Updated_Action_to_Execute),
    ("executed_action", C.Updated_Executed_Action),
    ("thresholds", C.Updated_Thresholds),
    ("internal_signals", C.Internal_Signals),
    ("perceptions", C.Updated_Perceptions),
    ("satisfied_desires", C.Updated_Satisfied_Desires),
)
_BROADCAST_FLAGS_AFTER_QUEUES = (
    ("important_beliefs", C.Updated_Critical_Beliefs),
    ("preconditions", C.Updated_Preconditions),
)


class GlobalWorkspace:
    """The Global Workspace (Baars): the shared blackboard that executives read and write, and the hub that
    broadcasts update signals. See the module docstring for the locking and the Java quirks.
    """
    def __init__(self, agent: Any):
        self.agent = agent
        self.plan_library = GlitterTrie()

        # Executive components (set by acquire_agent_components)
        self.attention_modulation_component: Any = None
        self.desire_promotion_component: Any = None
        self.executive_inhibition_function: Any = None
        self.executive_perception_function: Any = None
        self.executive_memory_maintenance_function: Any = None
        self.executive_reasoner_function: Any = None
        self.executive_resource_allocation_function: Any = None
        self.action_control: Any = None
        self.executive_switching_function: Any = None

        self.contatore_di_broadcast: int = 0
        self._counter_lock = threading.Lock()

        self._contracts_lock = threading.Lock()
        self.update_contracts: Dict[C, Dict[Any, None]] = {c: {} for c in C}
        self.message_handler = BaseMessageHandler()

        self.default_saliency_threshold = DoubleProtectedObject(0.3)
        self.default_attention_threshold = DoubleProtectedObject(self.default_saliency_threshold.read())
        self.saliency_threshold = DoubleProtectedObject(self.default_saliency_threshold.read())
        self.attention_threshold = DoubleProtectedObject(self.default_saliency_threshold.read())

        self.uninhibited_conscious_data = ConsciousData()
        self.list_uninhibited_beliefs: ProtectedList = ProtectedList()
        self.map_uninhibited_beliefs: Dict[str, Belief] = {}
        self.list_preconditions: ProtectedList = ProtectedList()
        self.list_important_beliefs: ProtectedList = ProtectedList()
        self.list_uninhibited_regions: ProtectedList = ProtectedList()
        self.map_uninhibited_regions: Dict[str, Region] = {}
        self.list_stimuli: ProtectedList = ProtectedList()
        self.list_filtered_stimuli: ProtectedList = ProtectedList()
        self.list_attentional_desires: ProtectedList = ProtectedList()
        self.list_uninhibited_desires: ProtectedList = ProtectedList()
        self.list_intentions: ProtectedList = ProtectedList()
        self.list_selected_intentions: AutoNamedProtectedList = AutoNamedProtectedList()
        self.is_focused = BooleanProtectedObject(False)

        self._lock_update_thresholds = threading.RLock()
        self._lock_uninhibited_desires = threading.RLock()
        self._lock_uninhibited_data = threading.RLock()
        self._lock_uninhibited_preconditions = threading.RLock()

        self.call_back: Optional[Callable] = None          # (pre, beliefs, desires, regions, gw)
        self.general_call_back: Optional[Callable] = None  # (update_message, gw)

    # ------------------------------------------------------------------ wiring
    def acquire_agent_components(self) -> None:
        """Fetch the references to the executive functions from the agent (done once the agent is fully built).
                
        """
        a = self.agent
        self.attention_modulation_component = a.get_attention_modulation_component()
        self.desire_promotion_component = a.get_desire_handler_component()
        self.executive_inhibition_function = a.get_executive_inhibition_function()
        self.executive_perception_function = a.get_executive_perception_function()
        self.action_control = a.get_action_control()
        self.executive_memory_maintenance_function = a.get_executive_memory_maintenance_function()
        self.executive_reasoner_function = a.get_executive_reasoner_function()
        self.executive_resource_allocation_function = a.get_executive_resource_allocation_function()
        self.executive_switching_function = a.get_executive_switching_function()

    def insert_for_update_contract(self, contract: C, who: Any) -> None:
        with self._contracts_lock:
            subscribers = self.update_contracts.get(contract)
            if subscribers is None:
                subscribers = {}
            if who not in subscribers:
                subscribers[who] = None
            self.update_contracts[contract] = subscribers

    def _subscribers(self, contract: C) -> List[Any]:
        with self._contracts_lock:
            return list(self.update_contracts[contract])

    def _ltm(self):
        return self.executive_memory_maintenance_function.get_lt_memory_maintenance()

    def set_call_back_set_generate_uninhibited_regions_for_intention(self, func: Optional[Callable]) -> None:
        self.call_back = func

    def set_general_call_back(self, func: Optional[Callable]) -> None:
        self.general_call_back = func

    # ------------------------------------------------------------------ thresholds
    def get_saliency_and_attention_thresholds(self) -> DoubleObject:
        with self._lock_update_thresholds:
            return DoubleObject(self.saliency_threshold.read(), self.attention_threshold.read())

    def update_saliency_and_attention_thresholds(self, saliency: float, attention: float) -> None:
        with self._lock_update_thresholds:
            self.saliency_threshold.write(saliency)
            self.attention_threshold.write(attention)
            self.broadcast_signal(C.Updated_Thresholds)

    def get_default_saliency_thresholds(self) -> float:
        return self.default_saliency_threshold.read()

    def get_default_attention_thresholds(self) -> float:
        return self.default_attention_threshold.read()

    def set_default_saliency_thresholds(self, value: float) -> None:
        self.default_saliency_threshold.write(value)

    def set_default_attention_thresholds(self, value: float) -> None:
        self.default_attention_threshold.write(value)

    # ------------------------------------------------------------------ intentions
    def _name_intention(self, intention: Intention) -> None:
        new_id = self.list_selected_intentions.inc_number.increment_and_get()
        if intention.get_name() is None or intention.get_name() == "":
            intention.set_name("Intention_" + str(new_id))

    def add_intentions(self, intentions: Optional[List[Intention]]) -> None:
        def action(lst: List[Intention]) -> None:
            if intentions:
                for intention in intentions:
                    self._name_intention(intention)
                    lst.append(intention)
        self.list_selected_intentions.modify_list(action)

    def add_intention(self, intention: Intention) -> None:
        def action(lst: List[Intention]) -> None:
            self._name_intention(intention)
            lst.append(intention)
        self.list_selected_intentions.modify_list(action)

    def set_intentions(self, intentions: Optional[List[Intention]]) -> None:
        def action(lst: List[Intention]) -> None:
            lst.clear()
            if intentions:
                for intention in intentions:
                    self._name_intention(intention)
                    lst.append(intention)
        self.list_selected_intentions.modify_list(action)

    def get_selected_intentions(self) -> List[Intention]:
        return self.list_selected_intentions.read()

    def set_selected_intentions(self, selected_intentions: List[Intention]) -> None:
        self.set_intentions(selected_intentions)
        self.broadcast_signal(C.Updated_Selected_Intentions)

    def update_selected_intentions(self, selected_intentions: List[Intention]) -> None:
        pass   # empty in Java

    def remove_intentions(self, intentions: List[Intention]) -> bool:
        result = self.list_selected_intentions.remove_all(intentions)
        for intention in intentions:
            intention.set_desire(None)
        return result

    # ------------------------------------------------------------------ desires (queries)
    def get_unhinibited_active_desires(self) -> List[AttentionalDesire]:
        return [d for d in self.list_uninhibited_desires.read()
                if d.get_status_desire() == TypeStatusDesire.Active]

    def get_unhinibited_desires(self) -> List[AttentionalDesire]:
        return self.list_uninhibited_desires.read()

    def get_active_practical_desires(self) -> List[PracticalDesire]:
        return [d for d in self.list_uninhibited_desires.read() if isinstance(d, PracticalDesire)]

    def _fill_attentional_desires_if_empty(self) -> None:
        if self.list_attentional_desires.is_empty():
            self.list_attentional_desires.add_all(self._ltm().get_attentional_desires())

    def get_attentional_desires(self) -> List[AttentionalDesire]:
        self._fill_attentional_desires_if_empty()
        return self.list_attentional_desires.read()

    def get_all_practical_desires(self) -> List[PracticalDesire]:
        return [d for d in self._ltm().get_attentional_desires() if isinstance(d, PracticalDesire)]

    def get_all_practical_desires_from_ltm(self) -> List[PracticalDesire]:
        self.list_attentional_desires.add_all(self._ltm().get_attentional_desires())
        return [d for d in self.list_attentional_desires.read() if isinstance(d, PracticalDesire)]

    def get_all_epistemic_desires(self) -> List[EpistemicDesire]:
        self._fill_attentional_desires_if_empty()
        return [d for d in self.list_attentional_desires.read() if isinstance(d, EpistemicDesire)]

    def get_epistemic_desires(self) -> List[EpistemicDesire]:
        return self.get_all_epistemic_desires()

    def get_inhibited_practical_desires_from_lt(self) -> List[PracticalDesire]:
        return [d for d in self._ltm().get_inhibited_attentional_desires() if isinstance(d, PracticalDesire)]

    def get_inhibited_attentional_desires_from_lt(self) -> List[AttentionalDesire]:
        return self._ltm().get_inhibited_attentional_desires()

    def get_inhibited_epistemic_desires(self) -> List[EpistemicDesire]:
        return [d for d in self._ltm().get_inhibited_attentional_desires() if isinstance(d, EpistemicDesire)]

    # ------------------------------------------------------------------ desire state changes
    def mark_as_active_desires(self, uninhibited_desires: List[AttentionalDesire],
                               inhibited_desires: List[AttentionalDesire]) -> None:
        """Promote desires (inhibited and uninhibited ones) to Active, add the data they need to the conscious
        data and broadcast ``Updated_Active_Desires``.
        """
        all_to_promote: Dict[AttentionalDesire, None] = dict.fromkeys(inhibited_desires)
        # keeps the data of the already uninhibited desires too
        all_to_promote.update(dict.fromkeys(uninhibited_desires))

        desires: List[AttentionalDesire] = []
        inhibited_desires_data: Optional[DesireData] = None
        if len(all_to_promote) > 0:
            inhibited_desires_data = self._recall_inhibited_data_for_activated_inhibited_desires(all_to_promote)
            desires.extend(all_to_promote)

        with self._lock_uninhibited_data:
            with self._lock_uninhibited_desires:
                if len(all_to_promote) > 0:
                    for desire in desires:
                        desire.set_status_desire(TypeStatusDesire.Active)
                    self._add_uninhibited_conscious_data(
                        inhibited_desires_data.get_preconditions(),
                        inhibited_desires_data.get_beliefs(),
                        desires,
                        inhibited_desires_data.get_regions())
                    self.broadcast_signal(C.Updated_Active_Desires)

    def mark_as_standing_desires(self, desires: List[AttentionalDesire]) -> None:
        """Send desires back to Standing: clear their options and detach and remove their intentions."""
        with self._lock_uninhibited_desires:
            intentions_to_remove: List[Intention] = []
            for desire in desires:
                desire.set_status_desire(TypeStatusDesire.Standing)
                desire.clear_options()
                intention = desire.get_related_intention()
                if intention is not None:
                    desire.set_related_intention(None)
                    intentions_to_remove.append(intention)
                    intention.set_desire(None)
            self.remove_intentions(intentions_to_remove)

    def mark_as_satisfied_desires(self, desires: List[AttentionalDesire]) -> None:
        """Mark desires Satisfied: detach and remove their intentions, move them from the attentional to the satisfied desires of the long-term memory and broadcast ``Updated_Selected_Intentions``.
        """
        with self._lock_uninhibited_desires:
            intentions_to_remove: List[Intention] = []
            for desire in desires:
                desire.set_status_desire(TypeStatusDesire.Satisfied)
                desire.clear_options()
                intention = desire.get_related_intention()
                desire.set_related_intention(None)
                if intention is not None:
                    intention.set_desire(None)
                    intentions_to_remove.append(intention)
            self.list_uninhibited_desires.remove_all(desires)
            self.list_attentional_desires.remove_all(desires)
            self._ltm().remove_attentional_desires(desires)
            self._ltm().add_satisfied_attentional_desires(desires)
            self.remove_intentions(intentions_to_remove)
            self.broadcast_signal(C.Updated_Selected_Intentions)

    # ------------------------------------------------------------------ broadcast
    def broadcast(self) -> None:
        """Forward every flag raised in the Global Workspace mailbox to the mailbox of each subscribed executive; the delete/satisfied intention queues are forwarded between the two groups of flags.
        """
        mh = self.message_handler
        for flag, contract in _BROADCAST_FLAGS_BEFORE_QUEUES:
            self._forward_flag(mh, flag, contract)

        delete_messages = list(mh.read_and_clear_internal_signals_delete_intention_messages())
        if len(delete_messages) > 0:
            for who in self._subscribers(C.Internal_Signals_Delete_Intention):
                for message in delete_messages:
                    who.message_handler.add_value_updated_internal_signals_delete_intention_message(
                        message.read_sender(), message.read_data_and_clean())

        satisfied_messages = list(mh.read_and_clear_internal_signals_satisfied_intention_messages())
        if len(satisfied_messages) > 0:
            for who in self._subscribers(C.Internal_Signals_Satisfied_Intention):
                for message in satisfied_messages:
                    who.message_handler.add_value_updated_internal_signals_satisfied_intention_message(
                        message.read_sender(), message.read_data_and_clean())

        for flag, contract in _BROADCAST_FLAGS_AFTER_QUEUES:
            self._forward_flag(mh, flag, contract)

    def _forward_flag(self, mh: BaseMessageHandler, flag: str, contract: C) -> None:
        if mh.read_value_and_clear(flag):
            for who in self._subscribers(contract):
                who.message_handler.write_value(flag)

    def _count_broadcast(self) -> None:
        with self._counter_lock:
            self.contatore_di_broadcast += 1

    def broadcast_signal(self, update_message: Optional[C]) -> None:
        """Count the broadcast, call the general callback, raise the flag of ``update_message`` (see the quirks above) and ``broadcast``. ``None`` does nothing.
        """
        if update_message is not None:
            self._count_broadcast()
            if self.general_call_back is not None:
                self.general_call_back(update_message, self)
            flag = _SIGNAL_FLAG.get(update_message)
            if flag is not None:
                self.message_handler.write_value(flag)
            self.broadcast()

    def broadcast_internal_signals_messages(self, update_message: Optional[C], sender_name: str,
                                            data: List[Any]) -> None:
        """Queue an internal signal (abort option, delete or satisfied intention) with its sender and data, then ``broadcast``.
        """
        if update_message is not None:
            self._count_broadcast()
            if update_message == C.Internal_Signals_Abort_Option:
                self.message_handler.add_value_updated_internal_signals_abort_option_message(sender_name, data)
            elif update_message == C.Internal_Signals_Delete_Intention:
                self.message_handler.add_value_updated_internal_signals_delete_intention_message(sender_name, data)
            elif update_message == C.Internal_Signals_Satisfied_Intention:
                self.message_handler.add_value_updated_internal_signals_satisfied_intention_message(sender_name, data)
            self.broadcast()

    # ------------------------------------------------------------------ beliefs / stimuli / regions
    def get_uninhibited_beliefs(self) -> List[Belief]:
        return self.list_uninhibited_beliefs.read()

    def get_uninhibited_regions(self) -> List[Region]:
        return self.list_uninhibited_regions.read()

    def get_all_attentional_desires_from_mm(self):
        return self._ltm().get_attentional_desires()

    def get_all_not_satisfied_attentional_desire_from_mm(self):
        return self._ltm().get_all_not_satisfied_attentional_desires()

    def get_all_beliefs_from_mm(self):
        return self._ltm().get_all_beliefs()

    def get_all_map_beliefs_from_mm(self):
        return self._ltm().get_all_map_beliefs()

    def get_all_regions_from_mm(self):
        return self._ltm().get_regions()

    def set_uninhibited_beliefs(self, beliefs: List[Belief]) -> None:
        self.list_uninhibited_beliefs.set_list(beliefs)
        self.map_uninhibited_beliefs.clear()
        for belief in beliefs:
            self.map_uninhibited_beliefs[belief.get_name()] = belief
        self.broadcast_signal(C.Updated_Uninhibited_Data)

    def get_action_control(self) -> Any:
        return self.action_control

    def get_inhibited_beliefs_from_mm(self):
        return self._ltm().get_inhibited_beliefs()

    def get_inhibited_regions_from_mm(self):
        return self._ltm().get_inhibited_regions()

    def set_beliefs(self, beliefs: List[Belief]) -> None:
        self._ltm().set_beliefs(beliefs)
        self.broadcast_signal(C.Updated_Beliefs)

    def get_stimuli(self) -> List[Stimulus]:
        return self.list_stimuli.read_and_clear()

    def get_filtered_stimuli(self) -> List[Stimulus]:
        return self.list_filtered_stimuli.read_and_clear()

    def set_stimuli(self, stimuli: List[Stimulus]) -> None:
        self.list_stimuli.set_list(stimuli)
        self.broadcast_signal(C.Updated_Stimuli)

    def set_filtered_stimuli(self, filtered_stimuli: List[Stimulus]) -> None:
        self.list_filtered_stimuli.set_list(filtered_stimuli)
        self.broadcast_signal(C.Updated_Filtered_Stimuli)

    def add_attentional_desires(self, desires: List[AttentionalDesire]) -> None:
        self._ltm().add_attentional_desires(desires)        # first in Long Memory ...
        self.list_attentional_desires.add_all(desires)      # ... then in the Global Workspace
        self.broadcast_signal(C.Updated_Standing_Desires)

    def add_inhibited_practical_attentional_desires(self, practical_desires_data: List[Any]) -> None:
        desires = [data.get_practical_desire() for data in practical_desires_data]
        self._ltm().add_inhibited_practical_desires(practical_desires_data)
        self._ltm().add_inhibited_desire(desires)
        self.broadcast_signal(C.Updated_Standing_Desires)

    def get_preconditions(self) -> List[Belief]:
        return self.list_preconditions.read()

    def get_important_beliefs(self) -> List[Belief]:
        return self.list_important_beliefs.read()

    def set_important_beliefs(self, beliefs: List[Belief]) -> None:
        self.list_important_beliefs.set_list(beliefs)

    def set_preconditions(self, beliefs: List[Belief]) -> None:
        self.list_preconditions.set_list(beliefs)

    def _rebuild_regions_map(self, regions: Iterable[Region]) -> None:
        self.map_uninhibited_regions.clear()
        for region in regions:
            self.map_uninhibited_regions[region.get_name()] = region

    def _rebuild_beliefs_map(self, beliefs: Iterable[Belief]) -> None:
        self.map_uninhibited_beliefs.clear()
        for belief in beliefs:
            self.map_uninhibited_beliefs[belief.get_name()] = belief

    def set_uninhibited_conscious_data(self, pre_conditions: List[Belief], uninhibited_beliefs: List[Belief],
                                       uninhibited_desires: List[AttentionalDesire],
                                       uninhibited_regions: List[Region]) -> None:
        """Replace the uninhibited preconditions, beliefs, desires and regions (under the data locks), call the callback and broadcast ``Updated_Uninhibited_Data``.
        """
        with self._lock_uninhibited_data:
            self.list_uninhibited_beliefs.clear()
            self.list_uninhibited_regions.clear()
            with self._lock_uninhibited_preconditions:
                self.list_preconditions.clear()
                self.list_preconditions.add_all(pre_conditions)
            self.list_uninhibited_beliefs.add_all(uninhibited_beliefs)
            self.list_uninhibited_regions.add_all(uninhibited_regions)
            self._rebuild_regions_map(uninhibited_regions)
            self._rebuild_beliefs_map(uninhibited_beliefs)
            with self._lock_uninhibited_desires:
                self.list_uninhibited_desires.clear()
                self.list_uninhibited_desires.add_all(uninhibited_desires)
            self.uninhibited_conscious_data.write(pre_conditions, uninhibited_beliefs,
                                                  uninhibited_desires, uninhibited_regions)
            if self.call_back is not None:
                self.call_back(pre_conditions, uninhibited_beliefs, uninhibited_desires,
                               uninhibited_regions, self)
            self.broadcast_signal(C.Updated_Uninhibited_Data)

    def _add_uninhibited_conscious_data(self, pre_conditions: List[Belief], uninhibited_beliefs: List[Belief],
                                        uninhibited_desires: List[AttentionalDesire],
                                        uninhibited_regions: List[Region]) -> None:
        # the caller (mark_as_active_desires) already holds the uninhibited-data lock
        """Add data to the uninhibited lists (caller holds the data lock), remove it from the inhibited data and broadcast ``Updated_Uninhibited_Data``.
        """
        with self._lock_uninhibited_preconditions:
            self.list_preconditions.add_all(pre_conditions)
        self.list_uninhibited_beliefs.add_all(uninhibited_beliefs)
        self.list_uninhibited_desires.add_all(uninhibited_desires)
        self.list_uninhibited_regions.add_all(uninhibited_regions)
        self._rebuild_regions_map(uninhibited_regions)       # arguments only (Java)
        self._rebuild_beliefs_map(uninhibited_beliefs)       # arguments only (Java)
        self.uninhibited_conscious_data.write(pre_conditions, uninhibited_beliefs,
                                              uninhibited_desires, uninhibited_regions)
        self._ltm().remove_inhibited_data(uninhibited_desires, uninhibited_beliefs, uninhibited_regions)
        self.broadcast_signal(C.Updated_Uninhibited_Data)

    def _remove_uninhibited_conscious_data(self, pre_conditions: List[Belief], uninhibited_beliefs: List[Belief],
                                           uninhibited_desires: List[AttentionalDesire],
                                           uninhibited_regions: List[Region]) -> None:
        """Remove data from the uninhibited lists and broadcast ``Updated_Uninhibited_Data``."""
        with self._lock_uninhibited_data:
            with self._lock_uninhibited_preconditions:
                self.list_preconditions.remove_all(pre_conditions)
            self.list_uninhibited_beliefs.remove_all(uninhibited_beliefs)
            self.list_uninhibited_regions.remove_all(uninhibited_regions)
            self._rebuild_regions_map(uninhibited_regions)
            self._rebuild_beliefs_map(uninhibited_beliefs)
            with self._lock_uninhibited_desires:
                self.list_uninhibited_desires.clear()
                self.list_uninhibited_desires.add_all(uninhibited_desires)
            self.broadcast_signal(C.Updated_Uninhibited_Data)

    def set_inhibited_conscious_data(self, inhibited_beliefs: List[Belief],
                                     inhibited_desires: List[AttentionalDesire],
                                     inhibited_regions: List[Region]) -> None:
        self._ltm().set_inhibited_data(inhibited_desires, inhibited_beliefs, inhibited_regions)

    # ------------------------------------------------------------------ Long Memory delegations
    def get_all_green_desires_from_mm(self):
        return self._ltm().get_all_green_desires()

    def get_green_desires_by_names_from_mm(self, names):
        return self._ltm().get_green_desires_by_names(names)

    def get_all_quality_desiresfrom_mm(self):
        return self._ltm().get_all_quality_desires()

    def get_quality_desires_by_names_from_mm(self, names):
        return self._ltm().get_quality_desires_by_names(names)

    def get_satisfied_attentional_desires_from_ltm(self):
        return self._ltm().get_satisfied_attentional_desires()

    def get_selected_beliefs_from_ltm(self, names) -> Dict[str, Belief]:
        return self._ltm().get_selected_beliefs(names)

    def get_selected_regions_from_ltm(self, names) -> Dict[str, Region]:
        return self._ltm().get_selected_regions(names)

    def get_all_map_regions_from_ltm(self) -> Dict[str, Region]:
        return self._ltm().get_all_map_regions()

    # ------------------------------------------------------------------ belief updates
    def update_uninhibited_conscious_beliefs(self, beliefs_to_change: Dict[str, Any]) -> None:
        """``beliefs_to_change``: belief name -> ["Subject" | "Object_Complement", new value]."""
        if len(beliefs_to_change) > 0:
            with self._lock_uninhibited_data:
                in_list_important_belief = False
                temp_important_belief = self.list_important_beliefs.read()
                names = set(beliefs_to_change.keys())
                self.map_uninhibited_beliefs.update(self.get_selected_beliefs_from_ltm(names))

                for belief_name in beliefs_to_change.keys():
                    belief = self.map_uninhibited_beliefs.get(belief_name)
                    if belief is None:
                        print("Error when Update_Uninhibited_Conscious_Beliefs on Belief_Name: ")
                        print("Belief_Name: " + belief_name)
                    else:
                        type_and_value = beliefs_to_change[belief_name]
                        change_type = type_and_value[0]
                        value = type_and_value[1]
                        if change_type == "Subject":
                            belief.get_predicate().set_subject(value)
                        else:   # "Object_Complement"
                            belief.get_predicate().set_object_complement(value)
                        belief.set_truth(True)
                        belief.set_time_stamp(datetime.now())
                        in_list_important_belief = in_list_important_belief or (belief in temp_important_belief)

                self.uninhibited_conscious_data.write(
                    self.list_preconditions.read(), list(self.map_uninhibited_beliefs.values()),
                    self.list_uninhibited_desires.read(), self.list_uninhibited_regions.read())
                self.broadcast_signal(C.Updated_Beliefs)
                if in_list_important_belief:
                    self.broadcast_signal(C.Updated_Critical_Beliefs)

    def get_map_uninhibited_beliefs(self) -> Dict[str, Belief]:
        with self._lock_uninhibited_data:
            return dict(self.map_uninhibited_beliefs)

    def get_map_uninhibited_regions(self) -> Dict[str, Region]:
        return dict(self.map_uninhibited_regions)

    def add_uninhibited_preconditions(self, pre_conditions: Optional[Iterable[Belief]]) -> None:
        if pre_conditions is not None:
            pre_conditions = list(pre_conditions)
            if len(pre_conditions) > 0:
                with self._lock_uninhibited_preconditions:
                    self.list_preconditions.add_all(pre_conditions)
                self.broadcast_signal(C.Updated_Preconditions)

    def _recall_inhibited_data_for_activated_inhibited_desires(
            self, desires_to_promote: Iterable[AttentionalDesire]) -> DesireData:
        """Collect from the long-term memory the preconditions and beliefs that desires about to become active need (by their trigger-condition and reasoner belief names).
        """
        result = DesireData()
        precondition_names: Dict[str, None] = {}
        beliefs_names: Dict[str, None] = {}
        regions_names: Dict[str, None] = {}
        for desire in desires_to_promote:
            if isinstance(desire, PracticalDesire):
                precondition_names.update(dict.fromkeys(desire.get_trigger_condition().get_beliefs_names()))
            elif isinstance(desire, EpistemicDesire):
                precondition_names[desire.get_belief_name()] = None
            else:
                raise ValueError(f"Unexpected value: {desire}")
            beliefs_names.update(dict.fromkeys(desire.get_beliefs_name_for_reasoner()))
            regions_names.update(dict.fromkeys(desire.get_regions_name_for_reasoner()))
        result.set_preconditions(list(self.get_selected_beliefs_from_ltm(set(precondition_names)).values()))
        result.set_beliefs(list(self.get_selected_beliefs_from_ltm(set(beliefs_names)).values()))
        return result

    def associate_functions_to_inhibited_desires(self, desires_data: List[Any]) -> None:
        """Register on the reasoner and inhibition executives the means-end, belief-inhibition and region-inhibition functions carried by the desire data.
        """
        for data in desires_data:
            practical_desire = data.get_practical_desire()
            self.executive_reasoner_function.register_practical_function(
                practical_desire.get_name(), data.get_means_end_reasoner_function())
            for func in data.get_beliefs_inhibition_functions():
                self.executive_inhibition_function.register_practical_belief_inhibition_function(
                    practical_desire.get_name(), func)
            for func in data.get_regions_inhibition_functions():
                self.executive_inhibition_function.register_practical_region_inhibition_function(
                    practical_desire.get_name(), func)

    # ------------------------------------------------------------------ plan library
    def insert_plan_in_plan_library(self, intention: Intention) -> bool:
        return self.plan_library.create_plan(intention)

    def get_plans_from_plan_library(self, attentional_desire: AttentionalDesire, preconditions: List[Any]):
        return self.plan_library.get_plans(attentional_desire, preconditions)

    def recal_beliefs(self, beliefs_names) -> Dict[str, Belief]:
        """Bring the named beliefs from the long-term memory into the uninhibited beliefs and return the updated name -> belief map.
        """
        with self._lock_uninhibited_data:
            uninhibited_beliefs = list(self.get_selected_beliefs_from_ltm(set(beliefs_names)).values())
            self.list_uninhibited_beliefs.add_all(uninhibited_beliefs)
            self._rebuild_beliefs_map(self.list_uninhibited_beliefs.read())
            self.uninhibited_conscious_data.write(
                self.list_preconditions.read(), self.list_uninhibited_beliefs.read(),
                self.list_uninhibited_desires.read(), self.list_uninhibited_regions.read())
            self._ltm().remove_inhibited_data(
                self.list_uninhibited_desires.read(), self.list_uninhibited_beliefs.read(),
                self.list_uninhibited_regions.read())
            return dict(self.map_uninhibited_beliefs)
