from unittest.mock import patch
from tasks.base.map_state import is_mirror_map

def test_all_map_transitions_use_retina_detection():
    with patch('tasks.base.map_state.auto.find_element',return_value=(1848,152)) as detect:
        assert is_mirror_map(take_screenshot=True)
    detect.assert_called_once_with('mirror/road_in_mir/legend_assets.png',model='retina',threshold=.9,take_screenshot=True)

def test_missing_map_does_not_complete_transition():
    with patch('tasks.base.map_state.auto.find_element',return_value=None):
        assert not is_mirror_map()

def test_shop_returns_after_map_reappears_instead_of_retrying_exit():
    from pathlib import Path
    from PIL import Image
    from module.automation import auto
    from module.config import cfg
    from module.macos.bootstrap import apply_mac_configuration
    from tasks.mirror.in_shop import Shop
    apply_mac_configuration(cfg)
    from utils.path_manager import path_manager
    path_manager.initialize_paths()
    scene=Image.new('L',(1920,1080))
    scene.paste(Image.open(Path(__file__).parent/'fixtures/map_marker_retina.png'),(1796,105))
    auto.screenshot=scene
    auto.clear_img_cache()
    shop=Shop.__new__(Shop)
    shop.ignore_shop=[True]*5
    with patch.object(auto,'take_screenshot',side_effect=[scene,AssertionError('shop exit retried after reaching map')]), patch.object(auto,'mouse_click_blank'), patch.object(auto,'click_element') as click, patch('tasks.mirror.in_shop.retry',return_value=True):
        shop.in_shop(1)
        click.assert_not_called()
