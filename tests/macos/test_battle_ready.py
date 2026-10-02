from pathlib import Path

import pytest
from PIL import Image

from module.automation import auto
from module.config import cfg
from module.macos.bootstrap import apply_mac_configuration
from tasks.battle.battle import battle_input_ready
from utils.path_manager import path_manager

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.mark.parametrize('name, ready', [
    ('battle_input_bright_arena.png', True),   # live: win_rate_card only 0.68 here
    ('battle_clash_animation.png', False),     # must not press P+Enter mid-clash
    ('map_bus_retina.png', False),
    ('theme_pack_floor_2.png', False),
    ('team_before_grace.png', False),
])
def test_input_phase_detected_by_gear(name, ready):
    apply_mac_configuration(cfg)
    path_manager.initialize_paths()
    auto.clear_img_cache()
    auto.screenshot = Image.open(FIXTURES / name).convert('L')
    assert battle_input_ready() is ready
