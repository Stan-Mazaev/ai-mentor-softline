from app.dialog.machine import initial_state, on_user_message
from app.dialog.states import DialogMode, DialogState


def test_info_starts_ready():
    assert initial_state(DialogMode.INFO) == DialogState.INFO_READY


def test_trainer_starts_awaiting():
    assert initial_state(DialogMode.TRAINER) == DialogState.AWAITING_ANSWER


def test_finished_rejects_new_message():
    t = on_user_message(DialogState.FINISHED, DialogMode.TRAINER)
    assert t.allowed is False


def test_info_loop_stays_ready():
    t = on_user_message(DialogState.INFO_READY, DialogMode.INFO)
    assert t.allowed
    assert t.next_state == DialogState.INFO_READY


def test_trainer_answer_loops_awaiting():
    t = on_user_message(DialogState.AWAITING_ANSWER, DialogMode.TRAINER)
    assert t.allowed
    assert t.next_state == DialogState.AWAITING_ANSWER