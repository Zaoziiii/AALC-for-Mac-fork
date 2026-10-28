from unittest.mock import patch

from module.macos import resize


def _info(width, height):
    return {'kCGWindowBounds': {'X': 1151, 'Y': -403, 'Width': width, 'Height': height}}


def test_fit_resizes_grown_window_back_to_1920_pixels():
    # Seen 2026-10-28: the frame drifted to 968x572 and the mail icon fell to 0.75.
    with patch.object(resize.window, 'info', return_value=_info(968, 572)), \
         patch.object(resize, '_display_scale', return_value=2.0), \
         patch.object(resize, 'resize_game', return_value='ok') as fit:
        assert resize.fit_game_window() is True
    fit.assert_called_once()


def test_fit_leaves_correct_window_alone():
    with patch.object(resize.window, 'info', return_value=_info(960, 568)), \
         patch.object(resize, '_display_scale', return_value=2.0), \
         patch.object(resize, 'resize_game') as fit:
        assert resize.fit_game_window() is False
    fit.assert_not_called()


def test_back_init_menu_closes_settings_instead_of_pressing_esc():
    from tasks.base import back_init_menu as menu
    clicks = []

    def click(target, *a, **k):
        clicks.append(target)
        if target == 'home/settings_return_assets.png':
            return len(clicks) == 1          # menu open on the first pass only
        return target == 'home/window_assets.png'

    with patch.object(menu, 'ensure_simulator_game_started', return_value=False), \
         patch.object(menu, 'retry', return_value=True), \
         patch.object(menu, 'update_model_for_retry'), \
         patch.object(menu.auto, 'click_element', side_effect=click), \
         patch.object(menu.auto, 'find_element', return_value=(1680, 187)), \
         patch.object(menu.auto, 'key_press') as esc:
        assert menu.back_init_menu() is True
    esc.assert_not_called()
    assert clicks[0] == 'home/settings_return_assets.png'
