from __future__ import annotations

from dataclasses import dataclass

from app.dialog.states import DialogMode, DialogState


@dataclass(frozen=True)
class Transition:
    next_state: DialogState
    allowed: bool


def initial_state(mode: DialogMode) -> DialogState:
    if mode == DialogMode.INFO:
        return DialogState.INFO_READY
    return DialogState.AWAITING_ANSWER


def on_user_message(current: DialogState, mode: DialogMode) -> Transition:
    if current == DialogState.FINISHED:
        return Transition(next_state=current, allowed=False)
    if mode == DialogMode.INFO and current == DialogState.INFO_READY:
        return Transition(next_state=DialogState.INFO_READY, allowed=True)
    if mode == DialogMode.TRAINER and current == DialogState.AWAITING_ANSWER:
        return Transition(next_state=DialogState.AWAITING_ANSWER, allowed=True)
    return Transition(next_state=current, allowed=False)