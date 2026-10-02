from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from module.automation import auto
from module.config import cfg
from module.macos.bootstrap import apply_mac_configuration
from tasks.mirror.mirror import Mirror
from utils.path_manager import path_manager

FIXTURES = Path(__file__).parent / 'fixtures'


def test_grace_retina_frame_reaches_selection_loop():
    apply_mac_configuration(cfg)
    path_manager.initialize_paths()
    auto.clear_img_cache()
    auto.screenshot = Image.open(FIXTURES / 'grace_retina.png').convert('L')
    mirror = Mirror.__new__(Mirror)
    # The old detector returns None and crashes while deriving card coordinates.
    with patch.object(auto, 'take_screenshot', side_effect=RuntimeError('selection loop reached')):
        with pytest.raises(RuntimeError, match='selection loop reached'):
            mirror.enter_mir_with_star()


def test_initial_gifts_keep_system_selected_across_retries():
    mirror = Mirror.__new__(Mirror)
    mirror.system = 'bleed'
    mirror.opening_items = False
    mirror.observe_ego_gift = False
    mirror.observe_ego_gift_selected = []
    system_clicks = []
    selected = set()
    frames = 0
    complete = False

    def screenshot():
        nonlocal frames
        frames += 1
        assert frames <= 6, 'selection never completed'
        return object()

    def find(target, **kwargs):
        return (100, 100) if complete and 'feature_theme_pack' in target else None

    def click(target, **kwargs):
        nonlocal complete
        if target.endswith('/bleed_gift_assets.png'):
            system_clicks.append(target)
            selected.clear()
            return True
        if '/select_init_gift/' in target:
            selected.add(target)
            return True
        if target.endswith('/select_init_ego_gifts_confirm_assets.png'):
            # One retry models a temporarily unavailable confirm button.
            complete = frames >= 3 and len(selected) == 3
            return complete
        return False

    with patch.object(auto, 'take_screenshot', screenshot), patch.object(auto, 'find_element', find), patch.object(auto, 'click_element', click), patch.object(auto, 'mouse_to_blank'), patch('tasks.mirror.mirror.retry', return_value=True), patch('tasks.mirror.mirror.sleep'):
        mirror.select_init_ego_gift()
    assert complete
    assert len(system_clicks) == 1, 'reselecting the system resets gift choices'


def test_team_screen_does_not_trigger_grace_selection():
    from tasks.base.opening_state import find_grace_anchor
    apply_mac_configuration(cfg)
    path_manager.initialize_paths()
    auto.clear_img_cache()
    auto.screenshot = Image.open(FIXTURES / 'team_before_grace.png').convert('L')
    assert not find_grace_anchor()
    mirror = Mirror.__new__(Mirror)
    with patch.object(auto, 'mouse_action_with_pos', side_effect=AssertionError('unexpected input')):
        assert mirror.enter_mir_with_star() is False
