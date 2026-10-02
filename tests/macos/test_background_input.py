import importlib.util
from unittest.mock import patch

import pytest
import Quartz as Q
from AppKit import NSEvent

from module.macos.geometry import GameGeometry
from module.macos.window import InputTarget
from module.my_error.my_error import userStopError

TARGET = InputTarget(123, 77, GameGeometry(100, 50, 1280, 745, 25))


def make_driver():
    name = 'module.automation.input_handlers.background'
    assert importlib.util.find_spec(name) is not None, 'Background input has not been implemented'
    from module.automation.input_handlers.background import BackgroundInput
    return BackgroundInput()


@pytest.fixture
def cursor():
    # Record cursor warps and hardware (dis)association; never touch the OS.
    log = []
    with patch('module.automation.input_handlers.background._cursor_location', return_value=(5, 6)), \
         patch('module.automation.input_handlers.background._user_idle_seconds', return_value=60.0), \
         patch.object(Q, 'CGWarpMouseCursorPosition', side_effect=lambda p: log.append(('warp', tuple(p)))), \
         patch.object(Q, 'CGAssociateMouseAndMouseCursorPosition', side_effect=lambda on: log.append(('associate', bool(on)))):
        yield log


@pytest.fixture
def sent(cursor):
    events = []
    # Construct real Quartz events, intercept only delivery to the OS.
    with patch('module.macos.window.window.input_target', return_value=TARGET), \
         patch('module.macos.window.window.info', return_value={'kCGWindowOwnerPID':123,'kCGWindowNumber':77}), \
         patch.object(Q, 'CGEventPostToPid', side_effect=lambda pid,event:events.append((pid,event))), \
         patch('pyautogui.moveTo', side_effect=AssertionError('must not move physical pointer')), \
         patch('pyautogui.click', side_effect=AssertionError('must not click foreground')), \
         patch.object(Q, 'CGEventPost', side_effect=AssertionError('must not post globally')):
        yield events


def test_click_targets_only_game_window_at_scaled_content_point(sent):
    driver = make_driver()
    driver.mouse_click(960,540)
    assert [Q.CGEventGetType(e) for _,e in sent] == [Q.kCGEventLeftMouseDown, Q.kCGEventLeftMouseUp]
    for pid,event in sent:
        assert pid == 123
        assert tuple(Q.CGEventGetLocation(event)) == (740,435)
        assert Q.CGEventGetIntegerValueField(event,Q.kCGMouseEventWindowUnderMousePointer) == 77
        assert Q.CGEventGetFlags(event) == 0
        assert NSEvent.eventWithCGEvent_(event).windowNumber() == 77


def test_cancelled_click_still_releases_to_original_process(sent):
    driver = make_driver()
    with patch('module.automation.input_handlers.background.wait_cancelled', side_effect=userStopError('stop')):
        with pytest.raises(userStopError):
            driver.mouse_click(960,540)
    assert [Q.CGEventGetType(e) for _,e in sent] == [Q.kCGEventLeftMouseDown,Q.kCGEventLeftMouseUp]


def test_keys_are_targeted_and_unsupported_keys_fail_without_input(sent):
    driver = make_driver()
    driver.key_press('enter')
    assert [Q.CGEventGetType(e) for _,e in sent] == [Q.kCGEventKeyDown,Q.kCGEventKeyUp]
    assert all(pid==123 for pid,_ in sent)
    assert all(NSEvent.eventWithCGEvent_(e).windowNumber()==77 for _,e in sent)
    assert Q.CGEventGetIntegerValueField(sent[0][1],Q.kCGKeyboardEventKeycode)==36
    with pytest.raises(ValueError):
        driver.key_press('unrecognized')
    assert len(sent)==2


def test_drag_release_on_window_move_does_not_retarget(sent):
    driver = make_driver()
    with patch('module.macos.window.window.input_target',side_effect=[TARGET,TARGET,userStopError('moved')]):
        with pytest.raises(userStopError):
            driver.mouse_drag(100,100,drag_time=0.1,dx=200)
    assert Q.CGEventGetType(sent[-1][1])==Q.kCGEventLeftMouseUp
    assert all(pid==123 for pid,_ in sent)
    assert all(NSEvent.eventWithCGEvent_(e).windowNumber()==77 for _,e in sent)


def test_unsupported_wheel_reports_failure_without_input(sent):
    driver = make_driver()
    assert driver.mouse_scroll(-3) is False
    assert sent == []


def test_text_does_not_touch_clipboard(sent):
    driver = make_driver()
    with patch('pyperclip.copy',side_effect=AssertionError('must not change clipboard')):
        driver.input_text('ABC')
    assert len(sent)==6
    assert all(pid==123 for pid,_ in sent)
    assert all(NSEvent.eventWithCGEvent_(e).windowNumber()==77 for _,e in sent)


def test_drag_moves_cursor_along_path_then_restores_it(sent, cursor):
    driver = make_driver()
    with patch('module.automation.input_handlers.background._sleep_uncancellable'):
        driver.mouse_drag_map(100, 100, drag_time=0.1, dx=200)
    assert cursor[0] == ('associate', False)
    assert cursor[-2:] == [('warp', (5, 6)), ('associate', True)]
    warps = [p for kind, p in cursor if kind == 'warp']
    assert warps[0] == tuple(TARGET.geometry.to_screen(100, 100))
    assert warps[-2] == tuple(TARGET.geometry.to_screen(300, 100))
    # Every drag frame is delivered where the cursor was warped.
    dragged = [e for _, e in sent if Q.CGEventGetType(e) == Q.kCGEventLeftMouseDragged]
    assert tuple(Q.CGEventGetLocation(dragged[-1])) == warps[-2]
    assert sum(Q.CGEventGetIntegerValueField(e, Q.kCGMouseEventDeltaX) for e in dragged) > 0


def test_interrupted_drag_still_restores_cursor(sent, cursor):
    driver = make_driver()
    with patch('module.macos.window.window.input_target', side_effect=[TARGET, TARGET, userStopError('moved')]), \
         patch('module.automation.input_handlers.background._sleep_uncancellable'):
        with pytest.raises(userStopError):
            driver.mouse_drag_map(100, 100, drag_time=0.1, dx=200)
    assert Q.CGEventGetType(sent[-1][1]) == Q.kCGEventLeftMouseUp
    assert cursor[-2:] == [('warp', (5, 6)), ('associate', True)]


def test_drag_waits_until_user_leaves_mouse_alone(sent, cursor):
    driver = make_driver()
    waits = []
    with patch('module.automation.input_handlers.background._user_idle_seconds', side_effect=[0.2, 1.0, 60.0]), \
         patch('module.automation.input_handlers.background.wait_cancelled', side_effect=waits.append), \
         patch('module.automation.input_handlers.background._sleep_uncancellable'):
        driver.mouse_drag_map(100, 100, drag_time=0.1, dx=200)
    # Two idle waits happen before the cursor is first touched.
    assert waits[:2] == [1.3, 0.5]
    assert cursor[0] == ('associate', False)


def test_battle_and_list_drags_stay_pure_background(sent, cursor):
    driver = make_driver()
    with patch('module.automation.input_handlers.background._user_idle_seconds', side_effect=AssertionError('must not wait')):
        driver.mouse_drag_link([(100, 100), (200, 100), (300, 100)])
        driver.mouse_drag(100, 100, drag_time=0.1, dy=200)
        driver.mouse_swipe_for_scroll(100, 100, duration=0.1, dy=200)
    assert cursor == []
    assert all(pid == 123 for pid, _ in sent)


def test_drag_ending_outside_the_game_is_clamped_not_rejected(sent):
    driver = make_driver()
    driver.mouse_drag(1686, 363, drag_time=0.1, dy=-500)   # live in_shop swipe
    last = sent[-1][1]
    assert Q.CGEventGetType(last) == Q.kCGEventLeftMouseUp
    assert tuple(Q.CGEventGetLocation(last)) == tuple(TARGET.geometry.to_screen(1686, 1))
