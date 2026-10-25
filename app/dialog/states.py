from enum import StrEnum


class DialogMode(StrEnum):
    INFO = "info"
    TRAINER = "trainer"


class DialogState(StrEnum):
    IDLE = "idle"
    INFO_READY = "info_ready"
    AWAITING_ANSWER = "awaiting_answer"
    FINISHED = "finished"


TERMINAL_STATES = {DialogState.FINISHED}