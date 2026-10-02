from unittest.mock import patch

import pytest
from PIL import Image

from module.macos.window import GameWindow
from module.my_error.my_error import userStopError


INFO = {'kCGWindowNumber': 77, 'kCGWindowOwnerPID': 123,
        'kCGWindowBounds': {'X': 100, 'Y': 50, 'Width': 1280, 'Height': 745}}


def test_background_capture_and_input_accept_occluded_window():
    window = GameWindow()
    window.background = True
    with patch('module.macos.window.require_permissions'), patch.object(window, 'info', return_value=INFO), \
         patch.object(window, 'assert_front', side_effect=userStopError('occluded')), \
         patch('module.macos.window.capture_window', return_value=Image.new('RGB', (1280, 745), 'red')):
        frame = window.capture(False)
        assert frame.size == (1920, 1080)
        assert frame.getpixel((960, 540)) == (255, 0, 0)
        assert window.input_geometry().to_screen(960, 540) == (740, 435)


def test_background_start_does_not_activate_application():
    window = GameWindow()
    window.background = True
    with patch('module.macos.window.require_permissions'), patch.object(window, 'info', return_value=INFO), \
         patch('module.macos.window.NSRunningApplication') as apps:
        window.focus()
        apps.runningApplicationWithProcessIdentifier_.assert_not_called()


def test_reused_window_id_in_another_process_is_rejected():
    window = GameWindow()
    window.last_capture_id = 77
    window.last_capture_pid = 123
    window.last_capture_geometry = window.geometry(INFO)
    new_process = {**INFO, 'kCGWindowOwnerPID': 999}
    with patch('module.macos.window.require_permissions'), patch.object(window, 'assert_front'), \
         patch.object(window, 'info', return_value=new_process), pytest.raises(userStopError):
        window.input_geometry()


def test_foreground_mode_still_rejects_occlusion():
    window = GameWindow()
    with patch('module.macos.window.require_permissions'), patch.object(window, 'info', return_value=INFO), \
         patch.object(window, 'assert_front', side_effect=userStopError('occluded')), pytest.raises(userStopError):
        window.capture()
