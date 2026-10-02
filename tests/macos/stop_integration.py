"""Native Qt regression: pause, stop, UI recovery and a fresh second task.
Run with the macOS venv; fake capture sends no input to the game.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
os.environ['AALC_DATA_DIR'] = tempfile.mkdtemp(prefix='aalc-stop-test-')
from module.macos.bootstrap import prepare_data_directory, apply_mac_configuration
prepare_data_directory()
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PIL import Image
from module.config import cfg
from module.automation import auto
from module.my_error.my_error import userStopError
from tasks.base.script_task_scheme import onetime_mir_process
from app.language_manager import LanguageManager
from app.my_app import MainWindow
app = QApplication([])
apply_mac_configuration(cfg)
LanguageManager().init_language()

# Both recovery layers must preserve the stop, rather than retry it.
auto.last_screenshot_time = 0
with patch('module.automation.automation.ScreenShot.take_screenshot', side_effect=userStopError('focus lost')) as capture:
    try:
        auto.take_screenshot()
    except userStopError:
        pass
    else:
        raise AssertionError('Screenshot swallowed stop')
    assert capture.call_count == 1
with patch('tasks.base.script_task_scheme.Mirror', side_effect=userStopError('cancelled')):
    try:
        onetime_mir_process(None, 1)
    except userStopError:
        pass
    else:
        raise AssertionError('Mirror swallowed stop')

ui = MainWindow(['AALC Mac'])
left = ui.farming_interface.interface_left
app.setQuitOnLastWindowClosed(False)
errors = []

def work(self):
    while True:
        auto.take_screenshot()

def stage(fn):
    def call():
        try:
            fn()
        except BaseException as exc:
            errors.append(exc)
            if left.my_script:
                left.my_script.terminate()
            app.quit()
    return call

def paused_stop():
    assert auto.check_pause()
    left.start_and_stop_tasks()

def restart():
    assert not left.my_script.isRunning(), 'Stop did not finish thread'
    assert left.link_start_button.isEnabled()
    assert left.link_start_button.get_text() == 'Link Start!'
    assert not auto.check_pause()
    left.start_and_stop_tasks()

def finish():
    assert not left.my_script.isRunning()
    assert left.link_start_button.isEnabled()
    assert left.link_start_button.get_text() == 'Link Start!'
    ui.close()
    app.quit()

with patch.object(left, 'check_setting', return_value=True), \
     patch('tasks.base.script_task_scheme.my_script_task._run', work), \
     patch('module.automation.automation.ScreenShot.take_screenshot', return_value=Image.new('L', (1920,1080))):
    left.start_and_stop_tasks()
    QTimer.singleShot(100, stage(left.pause_or_resume_tasks))
    QTimer.singleShot(200, stage(paused_stop))
    QTimer.singleShot(700, stage(restart))
    QTimer.singleShot(850, stage(left.start_and_stop_tasks))
    QTimer.singleShot(1400, stage(finish))
    app.exec()
if errors:
    raise errors[0]
print('PASS: stop propagation; native UI pause/stop; controls restored; second task stopped', flush=True)
