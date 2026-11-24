"""Java: TLong_Memory (data side: storage, XML loading, normalisation, inhibited data).

``Add_Inhibited_Practical_Desires`` and ``Acquire_Agent_Components`` (phase 4) are at the end of
the "desires" section / of the class.

Load order (as in Java ``Load_Data``): Predicates, Beliefs, Green, Quality, Epistemic, Practical;
then ``Normalize_Data``: predicates, beliefs, green, quality, PRACTICAL, epistemic; then
``Load_Other_Data`` (important beliefs from ``Critical_Beliefs.xml``).

Java quirks kept on purpose (see README, "Known Java quirks"):
* ``bug_compatible=True``: the epistemic loader reads the container tag ``Beliefs_for_Reasoner``
  instead of the item tag ``Belief_for_Reasoner``, so each epistemic desire gets ONE string
  with all belief names glued together. With ``bug_compatible=False`` the items are read.
* ``Map_Green_Desires`` / ``Map_Quality_Desires`` are never filled, so
  ``get_green_desires_by_names`` / ``get_quality_desires_by_names`` always return [].
* Java accumulates the epistemic loader's lists across desires (lists declared outside the
  loop); the case study has a single epistemic desire, so the lists are built per desire here.
* ``Critical_Beliefs.xml`` in the case study ``Data`` folder is intentionally empty (no
  ``Critical_Belief`` elements). If the file is missing, the error is printed and loading goes on,
  as in Java.
* The updated ``Beliefs.xml`` carries ``Confidence`` and ``Is_Stimulus`` per belief; ``load_beliefs``
  does not read them (the V0.3 Java logic does not use them).
"""
from __future__ import annotations

import os
import struct
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from .conscious_data import ConsciousData
from .desires import (AttentionalDesire, EpistemicDesire, GreenDesire, PracticalDesire, QualityDesire)
from .enums import TypeRelationship, TypeStatusDesire, TypeTemporalOperator
from .formula import PropositionalFormula, TemporalOperator, TemporalPropositionalFormula
from .model import Belief, DoubleObject, Predicate, Region, Stimulus
from .protected import AutoNamedProtectedList, ProtectedList, ProtectedObject
from .xmlio import (get_all_text_contents, get_document_xml, get_element_text_content)


def _parse_double(text: str) -> float:
    return float(text.replace(",", "."))


def _parse_bool(text: str) -> bool:
    return text.lower() == "true"  # Java Boolean.parseBoolean


def _parse_optional_time(text: str) -> Optional[datetime]:
    if text is None or text == "" or text == "null":
        return None
    return datetime.fromisoformat(text)


def _as_float32(value: float) -> float:
    return struct.unpack("f", struct.pack("f", value))[0]


class LongMemory:
    """Long-term memory: predicates, beliefs, desires (attentional, green, quality, satisfied), regions and the
    inhibited data, plus the XML loading/normalisation (Java: TLong_Memory). See the module docstring for
    the load order and the Java quirks kept.
    """
    def __init__(self, agent: Any = None, bug_compatible: bool = True):
        self.agent = agent
        self.bug_compatible = bug_compatible
        self.inc_attentional_desires_number = 0
        self.inc_practical_desires_number = ProtectedObject(0)
        self.inc_epistemic_desires_number = ProtectedObject(0)
        self.inhibited_conscious_data = ConsciousData()

        self.attentional_desires: AutoNamedProtectedList = AutoNamedProtectedList()
        self.satisfied_attentional_desires: AutoNamedProtectedList = AutoNamedProtectedList()
        self.inhibited_attentional_desires: ProtectedList = ProtectedList()
        self.green_desires: AutoNamedProtectedList = AutoNamedProtectedList()
        self.map_green_desires: Dict[str, GreenDesire] = {}
        self.quality_desires: AutoNamedProtectedList = AutoNamedProtectedList()
        self.map_quality_desires: Dict[str, QualityDesire] = {}
        self.beliefs: AutoNamedProtectedList = AutoNamedProtectedList()
        self.map_beliefs: Dict[str, Belief] = {}
        self.inhibited_beliefs: ProtectedList = ProtectedList()
        self.important_beliefs: ProtectedList = ProtectedList()
        self.regions: ProtectedList = ProtectedList()
        self.map_regions: Dict[str, Region] = {}
        self.inhibited_regions: ProtectedList = ProtectedList()
        self.predicates: AutoNamedProtectedList = AutoNamedProtectedList()
        self.map_predicates: Dict[str, Predicate] = {}
        self._lock_inhibited_data = threading.RLock()
        self.executive_memory_maintenance_function: Any = None

    # ------------------------------------------------------------------ desires
    def get_all_attentional_desires(self) -> List[AttentionalDesire]:
        return self.attentional_desires.read()

    def get_all_not_satisfied_attentional_desires(self) -> List[AttentionalDesire]:
        return [d for d in self.attentional_desires.read()
                if d.get_status_desire() != TypeStatusDesire.Satisfied]

    def get_all_satisfied_attentional_desires(self) -> List[AttentionalDesire]:
        return self.satisfied_attentional_desires.read()

    def get_satisfied_attentional_desires(self) -> List[AttentionalDesire]:
        return self.satisfied_attentional_desires.read()

    def add_satisfied_attentional_desires(self, desires: List[AttentionalDesire]) -> None:
        self.satisfied_attentional_desires.add_all(desires)

    def _register_desire(self, desire: AttentionalDesire) -> None:
        """Update the desire counters and give an unnamed desire the name 'Practical Desire n' / 'Epistemic
        Desire n'.
        """
        self.inc_attentional_desires_number = self.attentional_desires.inc_number.increment_and_get()
        if isinstance(desire, PracticalDesire):
            counter = self.inc_practical_desires_number
            prefix = "Practical Desire "
        elif isinstance(desire, EpistemicDesire):
            counter = self.inc_epistemic_desires_number
            prefix = "Epistemic Desire "
        else:
            raise ValueError(f"Unexpected value on Add_Attentional_Desire: {desire}")
        number = counter.read() + 1
        counter.write(number)
        if desire.get_name() is None or desire.get_name() == "":
            desire.set_name(prefix + str(number))

    def add_attentional_desires(self, desires: Optional[List[AttentionalDesire]]) -> None:
        def action(lst: List[AttentionalDesire]) -> None:
            if desires:
                for desire in desires:
                    self._register_desire(desire)
                    lst.append(desire)
        self.attentional_desires.modify_list(action)

    def _add_attentional_desire(self, desire: AttentionalDesire) -> None:
        def action(lst: List[AttentionalDesire]) -> None:
            self._register_desire(desire)
            lst.append(desire)
        self.attentional_desires.modify_list(action)

    def add_inhibited_practical_desires(self, desires_data) -> None:
        """Java: Add_Inhibited_Practical_Desires. Registers the practical desires carried by
        ``PracticalDesireData`` objects, associates the data's functions through the memory
        maintenance executive, publishes the trigger-condition beliefs as uninhibited
        pre-conditions and appends the desires to the attentional desires (NOT to the inhibited
        ones: the Global Workspace does that with ``add_inhibited_desire``)."""
        def action(lst: List[AttentionalDesire]) -> None:
            if desires_data:
                desires: List[AttentionalDesire] = []
                preconditions: List[Any] = []   # Java HashSet<TBelief>, may hold null
                for data in desires_data:
                    desire = data.get_practical_desire()
                    desires.append(desire)
                    self._register_desire(desire)
                    if desire.get_trigger_condition() is not None:
                        for belief_name in desire.get_trigger_condition().get_beliefs_names():
                            belief = self.map_beliefs.get(belief_name)
                            if belief not in preconditions:
                                preconditions.append(belief)
                self.executive_memory_maintenance_function.associate_functions_to_inhibited_desires(
                    desires_data)
                self.executive_memory_maintenance_function.add_uninhibited_preconditions(preconditions)
                lst.extend(desires)
        self.attentional_desires.modify_list(action)

    def remove_attentional_desires(self, desires: List[AttentionalDesire]) -> None:
        self.attentional_desires.remove_all(desires)

    def acquire_agent_components(self) -> None:
        """Java: Acquire_Agent_Components."""
        self.executive_memory_maintenance_function = self.agent.get_executive_memory_maintenance_function()

    def get_inhibited_attentional_desires(self) -> List[AttentionalDesire]:
        with self._lock_inhibited_data:
            return self.inhibited_attentional_desires.read()

    def clear_attentional_desires(self) -> None:
        self.attentional_desires.clear()

    def get_all_green_desires(self) -> List[GreenDesire]:
        return self.green_desires.read()

    def get_green_desires_by_names(self, names: List[str]) -> List[GreenDesire]:
        return [self.map_green_desires[n] for n in names if n in self.map_green_desires]

    def get_all_quality_desires(self) -> List[QualityDesire]:
        return self.quality_desires.read()

    def get_quality_desires_by_names(self, names: List[str]) -> List[QualityDesire]:
        return [self.map_quality_desires[n] for n in names if n in self.map_quality_desires]

    # ------------------------------------------------------------------ beliefs and predicates
    def get_all_beliefs(self) -> List[Belief]:
        return self.beliefs.read()

    def get_all_map_beliefs(self) -> Dict[str, Belief]:
        return dict(self.map_beliefs)

    def _add_belief_locked(self, lst: List[Belief], belief: Belief) -> None:
        new_id = self.beliefs.inc_number.increment_and_get()
        belief.set_belief_id(new_id)
        if belief.get_name() is None or belief.get_name() == "":
            belief.set_name("B_" + str(new_id))
        lst.append(belief)
        self.map_beliefs[belief.get_name()] = belief

    def add_beliefs(self, beliefs: Optional[List[Belief]]) -> None:
        def action(lst: List[Belief]) -> None:
            if beliefs:
                for belief in beliefs:
                    self._add_belief_locked(lst, belief)
        self.beliefs.modify_list(action)

    def add_belief(self, belief: Belief) -> None:
        self.beliefs.modify_list(lambda lst: self._add_belief_locked(lst, belief))

    def clear_beliefs(self) -> None:
        self.beliefs.clear()

    def add_predicate(self, predicate: Predicate) -> None:
        def action(lst: List[Predicate]) -> None:
            predicate.set_predicate_id(self.predicates.inc_number.increment_and_get())
            lst.append(predicate)
            self.map_predicates[predicate.get_name()] = predicate
        self.predicates.modify_list(action)

    def add_predicates(self, predicates: Optional[List[Predicate]]) -> None:
        def action(lst: List[Predicate]) -> None:
            if predicates:
                for predicate in predicates:
                    predicate.set_predicate_id(self.predicates.inc_number.increment_and_get())
                    lst.append(predicate)
                    self.map_predicates[predicate.get_name()] = predicate
        self.predicates.modify_list(action)

    def get_inhibited_beliefs(self) -> List[Belief]:
        with self._lock_inhibited_data:
            return self.inhibited_beliefs.read()

    def get_selected_beliefs(self, names) -> Dict[str, Belief]:
        return {n: self.map_beliefs[n] for n in names if n in self.map_beliefs}

    # ------------------------------------------------------------------ regions
    def get_all_regions(self) -> List[Region]:
        return self.regions.read()

    def get_all_map_regions(self) -> Dict[str, Region]:
        return self.map_regions

    def get_inhibited_regions(self) -> List[Region]:
        with self._lock_inhibited_data:
            return self.inhibited_regions.read()

    def add_region(self, region: Region) -> None:
        self.regions.add(region)
        self.map_regions[region.get_name()] = region

    def add_regions(self, regions: List[Region]) -> None:
        self.regions.add_all(regions)
        for region in regions:
            self.map_regions[region.get_name()] = region

    def clear_regions(self) -> None:
        self.regions.clear()
        self.map_regions.clear()

    def get_selected_regions(self, names) -> Dict[str, Region]:
        snapshot = dict(self.map_regions)
        return {n: snapshot[n] for n in names if n in snapshot}

    # ------------------------------------------------------------------ inhibited data
    def set_inhibited_data(self, inhibited_desires, inhibited_beliefs, inhibited_regions) -> None:
        """Replace the inhibited desires, beliefs and regions (under the inhibited-data lock) and mirror them
        in ``inhibited_conscious_data``.
        """
        with self._lock_inhibited_data:
            self.inhibited_attentional_desires.clear()
            self.inhibited_beliefs.clear()
            self.inhibited_regions.clear()
            self.inhibited_attentional_desires.set_list(inhibited_desires)
            self.inhibited_beliefs.set_list(inhibited_beliefs)
            self.inhibited_regions.set_list(inhibited_regions)
            self.inhibited_conscious_data.write(None, inhibited_beliefs, inhibited_desires, inhibited_regions)

    def _refresh_inhibited_conscious_data(self) -> None:
        self.inhibited_conscious_data.write(None, self.inhibited_beliefs.read(),
                                            self.inhibited_attentional_desires.read(),
                                            self.inhibited_regions.read())

    def add_inhibited_data(self, inhibited_desires, inhibited_beliefs, inhibited_regions) -> None:
        with self._lock_inhibited_data:
            self.inhibited_attentional_desires.add_all(inhibited_desires)
            self.inhibited_beliefs.add_all(inhibited_beliefs)
            self.inhibited_regions.add_all(inhibited_regions)
            self._refresh_inhibited_conscious_data()

    def add_inhibited_desire(self, inhibited_desires) -> None:
        with self._lock_inhibited_data:
            self.inhibited_attentional_desires.add_all(inhibited_desires)
            self._refresh_inhibited_conscious_data()

    def remove_inhibited_data(self, inhibited_desires, inhibited_beliefs, inhibited_regions) -> None:
        with self._lock_inhibited_data:
            self.inhibited_attentional_desires.remove_all(inhibited_desires)
            self.inhibited_beliefs.remove_all(inhibited_beliefs)
            self.inhibited_regions.remove_all(inhibited_regions)
            self._refresh_inhibited_conscious_data()

    # ------------------------------------------------------------------ XML loading
    @staticmethod
    def get_object_by_type_and_value(type_name: str, value: str) -> Any:
        """Convert an XML value to a Python object according to its Java type name (Boolean, Integer, Double,
        String, ...).
        """
        if type_name == "Boolean":
            return _parse_bool(value)
        if type_name in ("Byte", "Short", "Integer", "int", "Long"):
            return int(value)
        if type_name == "Char":
            return value[0]
        if type_name == "Double":
            return _parse_double(value)
        if type_name == "Float":
            return _as_float32(_parse_double(value))
        if type_name == "String":
            return value
        if type_name == "Object":
            return None
        if type_name == "Time":
            return datetime.fromisoformat(value)
        return DoubleObject(type_name, value)  # Predicate, Belief, ... normalised later

    def load_data(self, dir_path: str) -> None:
        """Load the six XML files (predicates, beliefs, green/quality/epistemic/practical desires) from
        ``dir_path``.
        """
        if dir_path is None or dir_path == "":
            print("TLong_Memory - error in Dir Path: " + str(dir_path), end="")
            return
        self.load_predicates(dir_path)
        self.load_beliefs(dir_path)
        self.load_green_desires(dir_path)
        self.load_quality_desires(dir_path)
        self.load_epistemic_desires(dir_path)
        self.load_practical_desires(dir_path)

    def load_predicates(self, dir_path: str) -> None:
        """Read ``Predicates.xml``."""
        root = get_document_xml(os.path.join(dir_path, "Predicates.xml"))
        if root is None:
            return
        for element in root.iter("Predicate"):
            name = get_element_text_content(element, "Predicate_Name")
            subject = self.get_object_by_type_and_value(get_element_text_content(element, "Subject_Type"),
                                                        get_element_text_content(element, "Subject_Value"))
            relationship = TypeRelationship(get_element_text_content(element, "Relationship_Type"))
            complement = self.get_object_by_type_and_value(
                get_element_text_content(element, "Object_Complement_Type"),
                get_element_text_content(element, "Object_Complement_Value"))
            self.add_predicate(Predicate(name, subject, relationship, complement))

    def load_beliefs(self, dir_path: str) -> None:
        """Read ``Beliefs.xml``."""
        root = get_document_xml(os.path.join(dir_path, "Beliefs.xml"))
        if root is None:
            return
        loaded: List[Belief] = []
        for element in root.iter("Belief"):
            name = get_element_text_content(element, "Belief_Name")
            belief_type = get_element_text_content(element, "Belief_Type")
            predicate_name = get_element_text_content(element, "Associated_Predicate")
            source = get_element_text_content(element, "Information_Source")
            time_stamp = _parse_optional_time(get_element_text_content(element, "Time_Stamp"))
            truth = _parse_bool(get_element_text_content(element, "Truth"))
            if belief_type.startswith("BLTS_"):
                loaded.append(Stimulus(name, predicate_name, 0.0, truth, source, time_stamp, belief_type))
            else:
                loaded.append(Belief(name, predicate_name, truth, source, time_stamp, belief_type))
        self.add_beliefs(loaded)

    def load_green_desires(self, dir_path: str) -> None:
        """Read ``Green_Desires.xml``."""
        root = get_document_xml(os.path.join(dir_path, "Green_Desires.xml"))
        if root is None:
            return
        loaded: List[GreenDesire] = []
        for element in root.iter("Green_Desire"):
            loaded.append(GreenDesire(
                get_element_text_content(element, "Green_Desire_Name"),
                get_element_text_content(element, "Constraint"),
                get_element_text_content(element, "Green_Desire_Type"),
                _parse_double(get_element_text_content(element, "Saliency")),
                _parse_double(get_element_text_content(element, "Reward")),
                _parse_double(get_element_text_content(element, "Relax_Preference")),
                _parse_double(get_element_text_content(element, "Fee"))))
        self.green_desires.add_all(loaded)

    def load_quality_desires(self, dir_path: str) -> None:
        """Read ``Quality_Desires.xml``."""
        root = get_document_xml(os.path.join(dir_path, "Quality_Desires.xml"))
        if root is None:
            return
        loaded: List[QualityDesire] = []
        for element in root.iter("Quality_Desire"):
            loaded.append(QualityDesire(
                get_element_text_content(element, "Quality_Desire_Name"),
                get_element_text_content(element, "Constraint"),
                get_element_text_content(element, "Quality_Desire_Type"),
                _parse_double(get_element_text_content(element, "Saliency")),
                _parse_double(get_element_text_content(element, "Reward")),
                _parse_double(get_element_text_content(element, "Relax_Preference"))))
        self.quality_desires.add_all(loaded)

    def load_epistemic_desires(self, dir_path: str) -> None:
        """Read ``Epistemic_Desires.xml`` (with the glued 'Beliefs_for_Reasoner' quirk when
        ``bug_compatible``).
        """
        root = get_document_xml(os.path.join(dir_path, "Epistemic_Desires.xml"))
        if root is None:
            return
        loaded: List[AttentionalDesire] = []
        for element in root.iter("Epistemic_Desire"):
            reasoner_tag = "Beliefs_for_Reasoner" if self.bug_compatible else "Belief_for_Reasoner"
            loaded.append(EpistemicDesire.from_names(
                get_element_text_content(element, "Epistemic_Name"),
                get_element_text_content(element, "Stimulus_Name"),
                get_element_text_content(element, "Trigger_condotion_formula"),
                get_all_text_contents(element, "Trigger_Condition_Name_Node"),
                _parse_double(get_element_text_content(element, "Saliency")),
                _parse_double(get_element_text_content(element, "Reward")),
                _parse_double(get_element_text_content(element, "Relax_Preference")),
                get_all_text_contents(element, "Green_Desire"),
                get_all_text_contents(element, "Quality_Desire"),
                get_all_text_contents(element, reasoner_tag),
                None))
        self.attentional_desires.add_all(list(loaded))
        self.inhibited_attentional_desires.add_all(list(loaded))

    def load_practical_desires(self, dir_path: str) -> None:
        """Read ``Practical_Desires.xml`` (formulas, time intervals, belief names)."""
        root = get_document_xml(os.path.join(dir_path, "Practical_Desires.xml"))
        if root is None:
            return
        loaded: List[AttentionalDesire] = []
        for element in root.iter("Practical_Desire"):
            loaded.append(PracticalDesire.from_names(
                get_element_text_content(element, "Practical_Name"),
                get_all_text_contents(element, "Belief_Temporal_Propositional_Formula"),
                get_all_text_contents(element, "Belief_Trigger_Condition_Formula"),
                get_element_text_content(element, "Temporal_Propositional_Formula"),
                get_element_text_content(element, "Trigger_Condition_Formula"),
                _parse_double(get_element_text_content(element, "Saliency")),
                _parse_double(get_element_text_content(element, "Reward")),
                _parse_double(get_element_text_content(element, "Relax_Preference")),
                get_all_text_contents(element, "Green_Desire"),
                get_all_text_contents(element, "Quality_Desire"),
                _parse_optional_time(get_element_text_content(element, "Finally_Start_Time")),
                _parse_optional_time(get_element_text_content(element, "Finally_End_Time")),
                None, None, None, None,
                get_all_text_contents(element, "Belief_for_Reasoner"),
                None))
        self.attentional_desires.add_all(list(loaded))
        self.inhibited_attentional_desires.add_all(list(loaded))

    # ------------------------------------------------------------------ normalisation
    def normalize_predicates(self) -> None:
        """Resolve predicate subjects/complements that refer to other predicates or beliefs by name."""
        beliefs = dict(self.map_beliefs)
        predicates = self.map_predicates
        for predicate in self.predicates.read():
            for index in (0, 1):
                obj = predicate.get_subject() if index == 0 else predicate.get_object_complement()
                if not isinstance(obj, DoubleObject):
                    continue
                kind, value = obj.get_object_first(), obj.get_object_second()
                if kind == "Predicate":
                    target = predicates.get(value)
                    what = "Predicate"
                elif kind == "Belief":
                    target = beliefs.get(value)
                    what = "Belief"
                else:
                    print("The Agent cannot to normalize the Subject of Object type: " + str(kind))
                    continue
                if target is not None:
                    if index == 0:
                        predicate.set_subject(target)
                    else:
                        predicate.set_object_complement(target)
                else:
                    print(f"No {what} to normalize for: {value}")

    def normalize_beliefs(self) -> None:
        predicates = dict(self.map_predicates)
        for belief in self.beliefs.read():
            predicate_name = belief.get_predicate_name()
            if belief.get_predicate() is None and predicate_name is not None and predicate_name.strip() != "":
                belief.set_predicate(predicates.get(predicate_name))  # missing predicate -> error, like Java NPE
            else:
                print(f"the agent failed to normalize the Predicate {predicate_name} of Belief: {belief.get_name()}")

    def _normalize_constraint_desires(self, desires, label: str) -> None:
        predicates = dict(self.map_predicates)
        for desire in desires:
            predicate_name = desire.get_constraint_name()
            if desire.get_constraint() is None and predicate_name is not None and predicate_name.strip() != "":
                desire.set_constraint(predicates.get(predicate_name))
            else:
                print(f"the agent failed to normalize the Predicate {predicate_name} of {label}: {desire.get_name()}")

    def normalize_green_desires(self) -> None:
        self._normalize_constraint_desires(self.green_desires.read(), "Green Desire")

    def normalize_quality_desires(self) -> None:
        self._normalize_constraint_desires(self.quality_desires.read(), "Quality Desire")

    def _resolve_green_quality(self, desire: AttentionalDesire, greens, qualities, label: str) -> None:
        """Replace the green/quality desire names of a desire by the loaded objects (prints a message for
        unknown names).
        """
        resolved_greens = []
        for name in desire.get_list_green_standing_desire_name():
            green = greens.get(name)
            if green is not None:
                resolved_greens.append(green)
            else:
                print(f"No Green Desire {name} to normalize for {label}: {desire.get_name()}")
        desire.set_list_green_standing_desire(resolved_greens)
        resolved_qualities = []
        for name in desire.get_list_quality_standing_desire_name():
            quality = qualities.get(name)
            if quality is not None:
                resolved_qualities.append(quality)
            else:
                print(f"No Quality Desire {name} to normalize for {label}: {desire.get_name()}")
        desire.set_list_quality_standing_desire(resolved_qualities)

    def normalize_epistemic_desires(self) -> None:
        """Resolve the belief, green and quality desires of every epistemic desire."""
        beliefs = dict(self.map_beliefs)
        greens = {g.get_name(): g for g in self.green_desires.read()}
        qualities = {q.get_name(): q for q in self.quality_desires.read()}
        for desire in self.attentional_desires.read():
            if not isinstance(desire, EpistemicDesire):
                continue
            belief = beliefs.get(desire.get_belief_name())
            if belief is not None:
                desire.set_belief(belief)
            else:
                print(f"No Belief {desire.get_belief_name()} to normalize for Epistemic Desire: {desire.get_name()}")
            self._resolve_green_quality(desire, greens, qualities, "Epistemic Desire")

    def normalize_practical_desires(self) -> None:
        """Resolve trigger/final-state beliefs, green and quality desires of every practical desire."""
        beliefs = dict(self.map_beliefs)
        greens = {g.get_name(): g for g in self.green_desires.read()}
        qualities = {q.get_name(): q for q in self.quality_desires.read()}
        for desire in self.attentional_desires.read():
            if not isinstance(desire, PracticalDesire):
                continue
            self._resolve_green_quality(desire, greens, qualities, "Practical Desire")

            trigger_beliefs = []
            for name in desire.get_trigger_condition_names():
                belief = beliefs.get(name)
                if belief is not None:
                    trigger_beliefs.append(belief)
                else:
                    print(f"No Trigger Condition  {name} to normalize for Practical Desire: {desire.get_name()}")
            trigger = PropositionalFormula()
            trigger.set_beliefs(trigger_beliefs)
            trigger.set_formula(desire.get_trigger_condition_formula())
            desire.set_trigger_condition(trigger)

            final_beliefs = []
            for name in desire.get_final_state_names():
                belief = beliefs.get(name)
                if belief is not None:
                    final_beliefs.append(belief)
                else:
                    print(f"No Final State  {name} to normalize for Practical Desire: {desire.get_name()}")
            operator = TemporalOperator()
            operator.set_type_temporal_operator(TypeTemporalOperator.Finally)
            operator.set_start_time(desire.get_finally_start())
            operator.set_end_time(desire.get_finally_end())
            final_state = TemporalPropositionalFormula()
            final_state.set_temporal_operator(operator)
            final_state.set_beliefs(final_beliefs)
            final_state.set_formula(desire.get_final_state_formula())
            final_state.set_list_temporal_propositional_formula_names(None)
            desire.set_final_state(final_state)

    def normalize_data(self) -> None:
        self.normalize_predicates()
        self.normalize_beliefs()
        self.normalize_green_desires()
        self.normalize_quality_desires()
        self.normalize_practical_desires()
        self.normalize_epistemic_desires()

    def load_critical_beliefs(self, dir_path: str) -> None:
        """Read ``Critical_Beliefs.xml`` (important beliefs); a missing file only prints an error, as in Java.
        """
        root = get_document_xml(os.path.join(dir_path, "Critical_Beliefs.xml"))
        if root is None:
            return
        loaded: List[Belief] = []
        for element in root.iter("Critical_Belief"):
            name = get_element_text_content(element, "Critical_Belief_Name")
            belief = self.map_beliefs.get(name)
            if belief is not None:
                loaded.append(belief)
            else:
                print("No Important Belief to load for Critical Belief: " + name)
        self.important_beliefs.add_all(loaded)

    def load_other_data(self, dir_path: str) -> None:
        self.load_critical_beliefs(dir_path)

    def initialize(self, dir_path: str) -> None:
        """Java: Initialize(Dir_Path). ``dir_path`` is the case study ``Data`` folder."""
        self.load_data(dir_path)
        self.normalize_data()
        self.load_other_data(dir_path)
