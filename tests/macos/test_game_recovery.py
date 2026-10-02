from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from module.macos import recovery
from module.my_error.my_error import userStopError

PS_RUNNING_GAME = ['/x/CrossOver Preview.app/Contents/SharedSupport/CrossOver/lib/wine/../../bin/wineserver',
                   r'C:\Program Files (x86)\Steam\steamapps\common\Limbus Company\LimbusCompany.exe ']
PS_CRASHED = PS_RUNNING_GAME[:1]


@pytest.fixture
def bottle(tmp_path):
    b = tmp_path / 'Bottles' / 'Steam'
    (b / recovery.GAME_DIR).mkdir(parents=True)
    (b / recovery.GAME_DIR / recovery.GAME_EXE).write_text('')
    (b / recovery.GAME_DIR / 'LimbusCompany_d3d11.log').write_text('err: device lost')
    (b / recovery.UNITY_LOG_DIR).mkdir(parents=True)
    (b / recovery.UNITY_LOG_DIR / 'Player.log').write_text('last frame')
    app = tmp_path / 'CrossOver Preview.app'
    (app / recovery.WINE_IN_APP).parent.mkdir(parents=True)
    (app / recovery.WINE_IN_APP).write_text('')
    ps = [f'{app}/Contents/SharedSupport/CrossOver/lib/wine/../../bin/wineserver']
    with patch.object(recovery, 'BOTTLES', b.parent), \
         patch.object(recovery, '_processes', return_value=ps), \
         patch.object(recovery, 'wait_cancelled'):
        yield b, app, tmp_path


def test_minimized_game_is_not_relaunched():
    with patch.object(recovery, '_processes', return_value=PS_RUNNING_GAME), \
         patch.object(recovery.subprocess, 'Popen', side_effect=AssertionError('must not relaunch')):
        with pytest.raises(userStopError, match='仍在运行'):
            recovery.GameRecovery().recover()


def test_crashed_game_is_relaunched_through_running_crossover(bottle):
    b, app, tmp = bottle
    with patch.object(recovery.subprocess, 'Popen') as popen, \
         patch('module.macos.window.find_game', side_effect=[userStopError('not yet'), {'kCGWindowNumber': 1}]), \
         patch.object(recovery.GameRecovery, 'save_crash_logs') as save, \
         patch.object(recovery.GameRecovery, 'wait_for_title') as title:
        recovery.GameRecovery().recover()
    title.assert_called_once()
    cmd = popen.call_args[0][0]
    assert cmd[0] == str(app / recovery.WINE_IN_APP)
    assert cmd[1:3] == ['--bottle', 'Steam']
    assert cmd[-2:] == ['-applaunch', '1973530']
    save.assert_called_once_with(b)


def test_crash_logs_are_copied_before_they_are_overwritten(bottle):
    b, _, tmp = bottle
    target = recovery.GameRecovery().save_crash_logs(b, log_root=tmp / 'logs')
    assert (target / 'LimbusCompany_d3d11.log').read_text() == 'err: device lost'
    assert (target / 'Player.log').read_text() == 'last frame'


def test_repeated_crashes_stop_the_task(bottle):
    r = recovery.GameRecovery()
    with patch.object(recovery.subprocess, 'Popen'), \
         patch('module.macos.window.find_game', return_value={}), \
         patch.object(recovery.GameRecovery, 'save_crash_logs'), \
         patch.object(recovery.GameRecovery, 'wait_for_title'):
        for _ in range(recovery.MAX_CRASHES):
            r.recover()
        with pytest.raises(userStopError, match='已停止自动重启'):
            r.recover()


def test_mirror_run_resumes_after_crash():
    from tasks.base import script_task_scheme as scheme
    runs = MagicMock(side_effect=[recovery.GameWindowLost('gone'), True])
    mirror = MagicMock()
    mirror.return_value.run = runs
    with patch.object(scheme, 'Mirror', mirror), \
         patch.object(recovery.game_recovery, 'recover') as recover, \
         patch.object(scheme, 'init_game') as init, \
         patch.object(scheme, 'back_init_menu') as menu, \
         patch.object(scheme, 'make_enkephalin_module'), \
         patch.object(scheme, 'check_hard_mirror_time', return_value=False):
        assert scheme.onetime_mir_process(MagicMock(), 1) is True
    recover.assert_called_once()
    init.assert_called_once()
    assert recovery.game_recovery.in_progress is False
    assert runs.call_count == 2
    assert menu.call_count == 2   # once to reach the menu after restart, once after finishing


def test_monitor_thread_keeps_running_when_window_is_lost():
    from tasks.base import retry_monitor as rm
    m = rm.RetryMonitor()
    m.poll_interval = 0
    calls = []
    def check_once():
        calls.append(1)
        if len(calls) == 1:
            raise recovery.GameWindowLost('gone')
        m._stop_event.set()
    m.check_once = check_once
    with patch('module.macos.control.cancel', side_effect=AssertionError('must not stop the task')):
        m._run()
    assert len(calls) == 2


def test_monitor_ignores_window_changes_while_recovering():
    from tasks.base import retry_monitor as rm
    m = rm.RetryMonitor()
    m.poll_interval = 0
    calls = []
    def check_once():
        calls.append(1)
        if len(calls) == 1:
            recovery.game_recovery.in_progress = True
            raise userStopError('游戏窗口位置或大小已改变，请重新开始')
        m._stop_event.set()
    m.check_once = check_once
    try:
        with patch('module.macos.control.cancel', side_effect=AssertionError('must not stop the task')):
            m._stop_event.clear()
            import threading
            t = threading.Thread(target=m._run); t.start()
            import time; time.sleep(0.2)
            recovery.game_recovery.finish()
            t.join(2)
    finally:
        recovery.game_recovery.in_progress = False
    assert len(calls) == 2


def test_recovery_flag_clears_when_recovery_fails():
    r = recovery.GameRecovery()
    with patch.object(recovery, '_processes', return_value=PS_RUNNING_GAME):
        with pytest.raises(userStopError):
            r.recover()
    assert r.in_progress is False
