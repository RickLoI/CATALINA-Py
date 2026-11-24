"""Attention selection (attention modulation) executive.

Java: TAttention_Selection, TAgent_Focus, TAgent_Unfocus.

On every change of the selected intentions: if the first intention's desire has options the agent
focuses (saliency threshold = saliency of that desire, attention threshold halfway between it and
1); otherwise it unfocuses (default thresholds, 0.3/0.3). The new thresholds go to the Global
Workspace (``update_saliency_and_attention_thresholds``), which broadcasts them. ``is_focused``
is true when both thresholds are equal, i.e. when UNfocused (Java naming, kept).
"""
from __future__ import annotations

from typing import Any, List

from .agent_thread import AgentBaseThread
from .enums import TypeUpdateContract as C
from .protected import BooleanProtectedObject, DoubleProtectedObject


class AgentFocus:
    """Computes the focused thresholds: saliency = saliency of the first intention's desire, attention halfway
    to 1.
    """
    def __init__(self, owner: Any):
        self.parent = owner
        self.saliency_threshold = 0.0
        self.attention_threshold = 0.0

    def execute(self, selected_intentions: List[Any]) -> None:
        intention = selected_intentions[0]
        if intention is not None and intention.get_active_desire() is not None:
            self.saliency_threshold = intention.get_active_desire().get_saliency()
            self.attention_threshold = self.saliency_threshold + ((1 - self.saliency_threshold) / 2)

    def get_saliency_threshold(self) -> float:
        return self.saliency_threshold

    def get_attention_threshold(self) -> float:
        return self.attention_threshold


class AgentUnfocus:
    """Computes the unfocused thresholds: the Global Workspace defaults (0.3 / 0.3)."""
    def __init__(self, owner: Any):
        self.parent = owner
        self.un_focused_saliency_threshold = 0.0
        self.un_focused_attention_threshold = 0.0

    def execute(self) -> None:
        gw = self.parent.get_global_workspace()
        self.un_focused_saliency_threshold = gw.get_default_saliency_thresholds()
        self.un_focused_attention_threshold = gw.get_default_attention_thresholds()

    def get_un_focused_saliency_threshold(self) -> float:
        return self.un_focused_saliency_threshold

    def get_un_focused_attention_threshold(self) -> float:
        return self.un_focused_attention_threshold


class AttentionSelection(AgentBaseThread):
    """Executive Attention Modulation thread: on every change of the selected intentions, focus or unfocus and
    publish the new thresholds.
    """
    DEFAULT_SALIENCY_THRESHOLD = 0.3

    def __init__(self, agent: Any):
        super().__init__(agent, "Executive Attention Modulation Function")
        self.global_workspace = self.agent.get_global_workspace()
        self.agent_focus = AgentFocus(self)
        self.agent_unfocus = AgentUnfocus(self)
        self.saliency_threshold = DoubleProtectedObject(self.DEFAULT_SALIENCY_THRESHOLD)
        self.attention_threshold = DoubleProtectedObject(self.DEFAULT_SALIENCY_THRESHOLD)
        self.is_focused = BooleanProtectedObject(False)
        self.selected_intentions: List[Any] = []

    def insert_in_list_update_contract(self) -> None:
        self.agent.get_global_workspace().insert_for_update_contract(C.Updated_Selected_Intentions, self)

    def execute(self) -> None:
        """React to a new selected-intentions list: focus if the first intention's desire has options,
        otherwise unfocus; then update the Global Workspace thresholds.
        """
        if self.message_handler.read_value_and_clear("selected_intentions"):
            self.selected_intentions = self.global_workspace.get_selected_intentions()
            if (len(self.selected_intentions) > 0 and
                    len(self.selected_intentions[0].get_active_desire().get_list_options()) > 0):
                self.agent_focus.execute(self.selected_intentions)
                self.saliency_threshold.write(self.agent_focus.get_saliency_threshold())
                self.attention_threshold.write(self.agent_focus.get_attention_threshold())
            else:
                self.agent_unfocus.execute()
                self.saliency_threshold.write(self.agent_unfocus.get_un_focused_saliency_threshold())
                self.attention_threshold.write(self.agent_unfocus.get_un_focused_attention_threshold())
            same = self.saliency_threshold.read() == self.attention_threshold.read()
            self.is_focused.write(same)
            self.global_workspace.is_focused.write(same)
            self.global_workspace.update_saliency_and_attention_thresholds(
                self.saliency_threshold.read(), self.attention_threshold.read())

    def get_global_global_workspace(self) -> Any:
        return self.global_workspace

    def get_global_workspace(self) -> Any:
        return self.global_workspace
