from unittest.mock import MagicMock, patch

import pytest

from module.macos import focus

GAME = 500


def app(pid, name):
    a = MagicMock()
    a.processIdentifier.return_value = pid
    a.localizedName.return_value = name
    a.isTerminated.return_value = False
    return a


@pytest.fixture
def world():
    state = {'front': app(42, 'Steam'), 'idle': 30.0}
    ws = MagicMock()
    ws.frontmostApplication.side_effect = lambda: state['front']
    workspace = MagicMock()
    workspace.sharedWorkspace.return_value = ws
    with patch.object(focus, 'NSWorkspace', workspace), \
         patch.object(focus, 'user_idle_seconds', side_effect=lambda: state['idle']), \
         patch.object(focus.log, 'warning') as warn:
        state['warn'] = warn
        yield state


def test_game_activated_right_after_input_is_undone_and_attributed(world):
    guard = focus.FocusGuard()
    steam = world['front']
    guard.check(GAME)
    world['front'] = app(GAME, 'LimbusCompany')
    guard.note(GAME, '按键')
    steam.activateWithOptions_.assert_called_once()
    assert '紧接在按键之后' in world['warn'].call_args[0][0]


def test_game_activating_itself_later_is_undone(world):
    guard = focus.FocusGuard()
    steam = world['front']
    guard.check(GAME)
    guard.last_action, guard.last_action_at = '点击', -100.0
    world['front'] = app(GAME, 'LimbusCompany')
    guard.check(GAME)
    steam.activateWithOptions_.assert_called_once()
    assert '游戏自行切到前台' in world['warn'].call_args[0][0]


def test_game_is_sent_back_even_if_the_user_was_active(world):
    guard = focus.FocusGuard()
    steam = world['front']
    guard.check(GAME)
    world['front'] = app(GAME, 'LimbusCompany')
    world['idle'] = 0.3
    guard.check(GAME)
    steam.activateWithOptions_.assert_called_once()


def test_paused_task_lets_the_game_stay_in_front(world):
    guard = focus.FocusGuard()
    guard.is_paused = lambda: True
    steam = world['front']
    guard.check(GAME)
    world['front'] = app(GAME, 'LimbusCompany')
    guard.check(GAME)
    guard.is_paused = lambda: False
    guard.check(GAME)   # resumed while the user is in the game: no stale restore
    steam.activateWithOptions_.assert_not_called()
    world['warn'].assert_not_called()
