from pathlib import Path
from unittest.mock import patch, Mock

import pytest
from PIL import Image
from module.automation import auto
from module.config import cfg
from module.macos.bootstrap import apply_mac_configuration
from module.my_error.my_error import userStopError
from tasks.mirror.mirror import Mirror
from utils.path_manager import path_manager

FIXTURE = Path(__file__).parent / 'fixtures/floor_panel_1.png'


def run_panel(image):
    apply_mac_configuration(cfg)
    path_manager.initialize_paths()
    auto.clear_img_cache()
    mirror = Mirror.__new__(Mirror)
    mirror.floor = 0
    mirror.mirror_map = Mock()
    def capture(gray=True):
        auto.screenshot = image.convert('L') if gray else image.copy()
        return auto.screenshot
    with patch.object(auto, 'take_screenshot', capture), patch.object(auto, 'mouse_action_with_pos'), patch.object(auto, 'mouse_click_blank'), patch('tasks.mirror.mirror.sleep'):
        # The real panel is already visible; bypass only its opening-button search.
        real_find = auto.find_element
        def find(target, *args, **kwargs):
            if target == 'mirror/road_in_mir/setting_assets.png':
                return (1847, 65)
            return real_find(target, *args, **kwargs)
        with patch.object(auto, 'find_element', find):
            mirror.get_which_floor()
    return mirror.floor


def test_live_first_floor_panel_is_not_zero():
    assert run_panel(Image.open(FIXTURE)) == 1


def test_unknown_panel_stops_instead_of_using_zero():
    with pytest.raises(userStopError):
        run_panel(Image.new('RGB', (1920,1080), 'black'))


@pytest.mark.parametrize('floor,x', [(2,854), (3,960), (4,1066), (5,1172)])
def test_active_diamond_position_selects_floor(floor, x):
    from tasks.base.floor_state import current_floor_from_panel
    # Controlled variations of the real panel, not live evidence for later floors.
    panel = Image.open(FIXTURE).convert('RGB')
    active = panel.crop((738,398,758,418))
    inactive = panel.crop((844,398,864,418))
    panel.paste(inactive,(738,398))
    panel.paste(active,(x-10,398))
    assert current_floor_from_panel(panel) == floor


def test_two_active_diamonds_are_ambiguous():
    from tasks.base.floor_state import current_floor_from_panel
    panel = Image.open(FIXTURE).convert('RGB')
    panel.paste(panel.crop((738,398,758,418)), (844,398))
    assert current_floor_from_panel(panel) is None


@pytest.mark.parametrize('floor', [2, 3])
def test_live_theme_title_updates_floor_without_clicking(floor):
    image = Image.open(FIXTURE.parent / f'theme_pack_floor_{floor}.png').convert('RGB')
    mirror = Mirror.__new__(Mirror)
    mirror.floor = 1
    mirror.mirror_map = Mock()
    with patch.object(auto, 'take_screenshot', return_value=image), \
         patch.object(auto, 'mouse_action_with_pos', side_effect=AssertionError('must not open panel')), \
         patch.object(auto, 'mouse_click_blank', side_effect=AssertionError('must not click title page')):
        mirror.get_which_floor(theme_pack=True)
    assert mirror.floor == floor
    mirror.mirror_map.refresh_floor.assert_called_once_with(floor)


@pytest.mark.parametrize('text,score,expected', [
    ('SELECT FLOOR 1 THEME PACK', .99, 1),
    ('SELECT FLOOR 3 THEME PACK', .99, 3),
    ('SELECT FLOOR 4 THEME PACK', .99, 4),
    ('SELECT FLOOR 5 THEME PACK', .99, 5),
    ('SELECT FL00R 3 THEME PACK', .99, 3),
    ('SELECT FLO0R 4 THEME PACK', .99, 4),
    ('SELECT FL0OR 5 THEME PACK', .99, 5),
    ('SELECT FL00R O THEME PACK', .99, None),
    ('SELECT FLOOR 12 THEME PACK', .99, None),
    ('SELECT FLOOR 0 THEME PACK', .99, None),
    ('SELECT FLOOR 6 THEME PACK', .99, None),
    ('Exploring Floor 2', .99, None),
    ('SELECT FLOOR 2 THEME PACK', .50, None),
])
def test_theme_title_requires_complete_confident_valid_floor(text, score, expected):
    from tasks.base.floor_state import current_floor_from_theme_pack
    from module.ocr import ocr
    result = Mock(txts=(text,), scores=(score,))
    with patch.object(ocr, 'run', return_value=result):
        assert current_floor_from_theme_pack(Image.new('RGB', (1920,1080))) == expected


def test_unknown_theme_title_stops_without_reusing_previous_floor():
    mirror = Mirror.__new__(Mirror)
    mirror.floor = 1
    mirror.mirror_map = Mock()
    with patch.object(auto, 'take_screenshot', return_value=Image.new('RGB', (1920,1080))), \
         patch.object(auto, 'mouse_action_with_pos', side_effect=AssertionError('must not open panel')), \
         patch('tasks.mirror.mirror.sleep'):
        with pytest.raises(userStopError, match='标题'):
            mirror.get_which_floor(theme_pack=True)
    mirror.mirror_map.refresh_floor.assert_not_called()
