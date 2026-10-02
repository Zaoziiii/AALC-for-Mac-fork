from threading import Event
from module.my_error.my_error import userStopError
_cancelled = Event()

def cancel():
    _cancelled.set()

def reset():
    _cancelled.clear()

def check_cancelled():
    if _cancelled.is_set():
        raise userStopError('任务已停止')


def wait_cancelled(seconds):
    """Wait without delaying a requested stop."""
    _cancelled.wait(seconds)
    check_cancelled()
