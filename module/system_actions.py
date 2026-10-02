"""macOS sleep prevention while the task engine is active."""
import atexit
import subprocess
import threading
from module.config import cfg
from module.logger import log
from module.after_completion_types import normalize_after_completion_config

_lock=threading.Lock()
_assertion=None
_depth=0

def apply_power_keep_awake(enable):
    global _assertion, _depth
    with _lock:
        _depth=max(0,_depth+(1 if enable else -1))
        if _depth and _assertion is None:
            _assertion=subprocess.Popen(['/usr/bin/caffeinate','-di','-w',str(__import__('os').getpid())])
        elif not _depth and _assertion is not None:
            _assertion.terminate()
            _assertion.wait(timeout=5)
            _assertion=None


def _cleanup():
    global _depth
    _depth=1
    apply_power_keep_awake(False)
atexit.register(_cleanup)

def get_after_completion_config():
    return [], 'none'

def set_after_completion_config(actions,power_action):
    cfg.set_value('after_completion_actions',[])
    cfg.set_value('after_completion_power_action','none')

def autodaily_exit_to_after_completion_config(exit_setting):
    return [], 'none'

def execute_after_completion(actions,power_action):
    if actions or power_action != 'none':
        log.warning('Mac 版不执行关机、退出游戏或模拟器等收尾操作')
    return False
