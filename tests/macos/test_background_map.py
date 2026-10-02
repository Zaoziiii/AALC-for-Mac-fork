from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from module.automation import auto
from module.config import cfg
from module.macos.bootstrap import apply_mac_configuration
from module.my_error.my_error import userStopError
from tasks.mirror import search_road as road
from utils.path_manager import path_manager


def test_retina_bus_visible_in_actual_frame():
    apply_mac_configuration(cfg)
    path_manager.initialize_paths()
    auto.clear_img_cache()
    auto.screenshot = Image.open(Path(__file__).parent / 'fixtures/map_bus_retina.png').convert('L')
    assert road.find_map_bus() == (409, 555)
    auto.screenshot = Image.new('L', (1920, 1080))
    assert road.find_map_bus() is None


@pytest.mark.parametrize('name, expected', [
    ('map_bus_reward_icons.png', (1235, 306)),   # live 0.808: reward icons over the bus
    ('theme_pack_floor_2.png', None),
    ('theme_pack_floor_3.png', None),
    ('team_before_grace.png', None),
    ('floor_panel_1.png', None),
])
def test_bus_partly_covered_is_found_without_false_positives(name, expected):
    apply_mac_configuration(cfg)
    path_manager.initialize_paths()
    auto.clear_img_cache()
    auto.screenshot = Image.open(Path(__file__).parent / 'fixtures' / name).convert('L')
    assert road.find_map_bus() == expected


def test_visible_route_uses_connected_nodes_and_returns_only_next_step():
    nodes = [['battle', (1085, 428)], ['shop', (1085, 750)], ['event', (1085, 109)]]
    links = [(1, road.Row.MID, road.Row.MID), (1, road.Row.MID, road.Row.TOP)]
    with patch.object(road, 'find_map_bus', return_value=(704, 396)), \
         patch.object(road, 'identify_nodes', return_value=nodes), \
         patch.object(road, 'identify_road', return_value=links), \
         patch.object(auto, 'mouse_drag_map', side_effect=AssertionError('background map must not drag')):
        directions, classes = road.search_road_visible()
    assert directions == ['U']
    assert classes == ['event']


def test_missing_bus_stops_without_blind_drag():
    with patch.object(road, 'find_map_bus', return_value=None), \
         patch.object(auto, 'mouse_drag_map', side_effect=AssertionError('blind drag')):
        with pytest.raises(userStopError, match='巴士'):
            road.search_road_visible()


@pytest.mark.parametrize('nodes', [None, [['battle', (1466, 111)]]])
def test_real_occluded_shop_arrow_remains_walkable(nodes):
    apply_mac_configuration(cfg)
    path_manager.initialize_paths()
    auto.clear_img_cache()
    image = Image.open(Path(__file__).parent / 'fixtures/map_occluded_shop.png')
    def capture(gray=True):
        auto.screenshot = image.convert('L' if gray else 'RGB')
        return auto.screenshot
    with patch.object(auto, 'take_screenshot', capture), \
         patch.object(road, 'identify_nodes', return_value=nodes), \
         patch.object(auto, 'mouse_drag_map', side_effect=AssertionError('must not drag')):
        assert road.search_road_visible() == (['U'], ['unknown'])


def test_classified_nodes_without_outgoing_arrow_are_not_walkable():
    with patch.object(road, 'find_map_bus', return_value=(704,396)), \
         patch.object(road, 'identify_nodes', return_value=[['shop', (1085, 109)]]), \
         patch.object(road, 'identify_road', return_value=[]):
        with pytest.raises(userStopError):
            road.search_road_visible()


def test_background_map_plans_full_route_once_and_uses_native_keys():
    with patch.object(cfg, 'get_value', side_effect=lambda key, default=None: {'background_click': True, 'mirror_keyboard_navigation': False}.get(key, default)), \
         patch.object(road, 'search_road_from_road_map', return_value=(['U', 'D'], ['bus', 'event', 'shop'])) as plan, \
         patch.object(road, 'search_road_visible', side_effect=AssertionError('route was planned')), \
         patch.object(road, 'visible_choices', return_value=[((False, 1), 'D', 'event'), ((False, 4), 'M', 'battle')]), \
         patch.object(auto, 'key_press') as key, \
         patch.object(road, '_keyboard_enter_succeeded', return_value=True), \
         patch.object(road, 'sleep'):
        mirror_map = road.MirrorMap()
        assert mirror_map.get_next_step() == 'U'
        assert mirror_map.enter_next_node('U')
        assert mirror_map.get_next_step() == 'D'
        assert plan.call_count == 1
        key.assert_called_once_with('up')


def test_background_falls_back_to_arrows_when_route_planning_fails():
    with patch.object(cfg, 'get_value', side_effect=lambda key, default=None: {'background_click': True}.get(key, default)), \
         patch.object(road, 'search_road_from_road_map', return_value=([], [])), \
         patch.object(road, 'search_road_visible', return_value=(['M'], ['event'])) as visible:
        assert road.MirrorMap().get_next_step() == 'M'
        visible.assert_called_once()


def test_route_planning_prefers_event_over_battle():
    # bus(MID) -> column2: TOP event / MID battle -> column3: MID battle
    columns = [[['event', (1085, 109)], ['battle', (1085, 396)]], [['battle', (1605, 396)]]]
    links = [(1, road.Row.MID, road.Row.TOP), (1, road.Row.MID, road.Row.MID),
             (2, road.Row.TOP, road.Row.MID), (2, road.Row.MID, road.Row.MID)]
    with patch.object(cfg, 'get_value', side_effect=lambda key, default=None: {'set_win_size': 1080}.get(key, default)):
        graph = road.RouteGraph(columns, road.Row.MID, (704, 396))
        graph.init_road(links)
        _, path = graph.find_min_weight_route()
        directions, classes = graph.get_path_directions(path)
    assert directions[0] == 'U' and classes[1] == 'event'


def test_background_failure_cannot_fall_through_to_drag_navigation():
    from tasks.mirror.mirror import Mirror
    mirror = Mirror.__new__(Mirror)
    mirror.mirror_map = road.MirrorMap()
    with patch.object(cfg, 'get_value', side_effect=lambda key, default=None: {'background_click': True, 'mirror_keyboard_simple_pathfinding': False}.get(key, default)), \
         patch.object(mirror.mirror_map, 'get_next_step', return_value=False), \
         patch.object(auto, 'mouse_to_blank'), \
         patch('tasks.mirror.mirror.search_road_default_distance', side_effect=AssertionError('unsafe fallback')):
        with pytest.raises(userStopError, match='后台寻路'):
            mirror.search_road()


def background(**extra):
    values = {'background_click': True, **extra}
    return patch.object(cfg, 'get_value', side_effect=lambda key, default=None: values.get(key, default))


def test_cached_step_not_shown_by_arrows_takes_best_arrow_and_replans_later():
    mirror_map = road.MirrorMap()
    mirror_map.floor_map = ['U', 'M']
    with background(), \
         patch.object(road, 'visible_choices', return_value=[((False, 1), 'D', 'event'), ((False, 4), 'M', 'battle')]), \
         patch.object(road, 'search_road_from_road_map', side_effect=AssertionError('must not drag now')):
        assert mirror_map.get_next_step() == 'D'
    assert mirror_map.floor_map == []


def test_cached_step_without_visible_arrows_replans():
    mirror_map = road.MirrorMap()
    mirror_map.floor_map = ['U']
    with background(), \
         patch.object(road, 'visible_choices', return_value=[]), \
         patch.object(road, 'search_road_from_road_map', return_value=(['M', 'D'], ['bus', 'event', 'shop'])) as plan:
        assert mirror_map.get_next_step() == 'M'
    plan.assert_called_once()
    assert mirror_map.floor_map == ['D']


def test_foreground_follows_cache_without_arrow_checks():
    mirror_map = road.MirrorMap()
    mirror_map.floor_map = ['U']
    with patch.object(cfg, 'get_value', side_effect=lambda key, default=None: {'background_click': False}.get(key, default)), \
         patch.object(road, 'visible_choices', side_effect=AssertionError('foreground unchanged')):
        assert mirror_map.get_next_step() == 'U'


def test_missing_bus_before_any_drag_reports_that_no_drag_happened():
    with patch.object(auto, 'click_element', return_value=False), \
         patch.object(road, 'find_map_bus', return_value=None), \
         patch.object(auto, 'mouse_drag_map', side_effect=AssertionError('must not drag')):
        with pytest.raises(userStopError, match='地图上未识别到巴士'):
            road.search_road_from_road_map()


def _plan_single_row(background_click):
    # Live 18:48: after the drag, three battles in one row above the bus.
    nodes = [['battle', (415, 256)], ['battle', (741, 258)], ['battle', (1066, 262)]]
    values = {'background_click': background_click, 'set_win_size': 1080}
    links = {1: (1, road.Row.MID, road.Row.TOP), 2: (2, road.Row.TOP, road.Row.TOP), 3: (3, road.Row.TOP, road.Row.TOP)}
    def fake_roads(bus, columns, bus_row):
        return [links[i + 1] for i in range(len(columns))]
    with patch.object(cfg, 'get_value', side_effect=lambda key, default=None: values.get(key, default)), \
         patch.object(auto, 'click_element', return_value=False), \
         patch.object(road, 'find_map_bus', return_value=(92, 508)), \
         patch.object(road, 'identify_nodes', return_value=nodes), \
         patch.object(road, 'identify_road', side_effect=fake_roads):
        return road.search_road_from_road_map()


def test_background_single_row_caches_the_whole_route():
    directions, classes = _plan_single_row(True)
    assert directions[:3] == ['U', 'M', 'M']
    assert classes[1:4] == ['battle', 'battle', 'battle']


def test_foreground_single_row_keeps_original_single_step():
    assert _plan_single_row(False) == (['U'], ['unknown'])


def test_node_classes_are_not_all_battle():
    # OpenCV 5 minMaxLoc returned class 0 for every node; the event must be seen.
    apply_mac_configuration(cfg)
    path_manager.initialize_paths()
    frame = Image.open(Path(__file__).parent / 'fixtures/map_default_color.png').convert('RGB')
    def capture(gray=True):
        auto.screenshot = frame.convert('L') if gray else frame
        return auto.screenshot
    with patch.object(auto, 'take_screenshot', capture):
        nodes = road.identify_nodes(0)
    classes = {tuple(p): c for c, p in nodes}
    assert classes[(579, 326)] == 'event'
    assert classes[(578, 54)] == 'battle'


def test_no_nodes_detected_falls_back_to_bus_arrows():
    # Live 20:17: only the boss was left and the detector returned nothing.
    values = {'background_click': True, 'set_win_size': 1080}
    with patch.object(cfg, 'get_value', side_effect=lambda key, default=None: values.get(key, default)), \
         patch.object(auto, 'click_element', return_value=False), \
         patch.object(road, 'find_map_bus', return_value=(82, 518)), \
         patch.object(road, 'identify_nodes', return_value=None), \
         patch.object(road, 'search_road_visible', return_value=(['M'], ['unknown'])) as arrows:
        assert road.MirrorMap().get_next_step() == 'M'
    arrows.assert_called_once()


def test_swallowed_key_falls_back_to_clicking_the_node():
    with patch.object(cfg, 'get_value', side_effect=lambda key, default=None: {'background_click': True}.get(key, default)), \
         patch.object(auto, 'key_press'), \
         patch.object(auto, 'mouse_click') as click, \
         patch.object(road, '_keyboard_enter_succeeded', side_effect=[False, False, True]), \
         patch.object(road.MirrorMap, '_get_next_position', return_value=[1079, 433]), \
         patch.object(road, 'sleep'):
        assert road.MirrorMap().enter_next_node('M')
    click.assert_called_once_with(1079, 433)


def test_background_search_retries_twice_then_stops():
    from tasks.mirror import mirror as mirror_module
    mirror = mirror_module.Mirror.__new__(mirror_module.Mirror)
    mirror.mirror_map = road.MirrorMap()
    with patch.object(cfg, 'get_value', side_effect=lambda key, default=None: {'background_click': True, 'mirror_keyboard_simple_pathfinding': False}.get(key, default)), \
         patch.object(mirror.mirror_map, 'get_next_step', side_effect=[TypeError("object of type 'bool' has no len()"), 'M', 'U']) as plan, \
         patch.object(mirror.mirror_map, 'enter_next_node', side_effect=[False, True]), \
         patch.object(mirror_module, 'sleep'), \
         patch.object(auto, 'mouse_to_blank'):
        assert mirror.search_road() is True     # crash, then failure, then success
    assert plan.call_count == 3
    with patch.object(cfg, 'get_value', side_effect=lambda key, default=None: {'background_click': True, 'mirror_keyboard_simple_pathfinding': False}.get(key, default)), \
         patch.object(mirror.mirror_map, 'get_next_step', return_value='M') as plan, \
         patch.object(mirror.mirror_map, 'enter_next_node', return_value=False), \
         patch.object(mirror_module, 'sleep'), \
         patch.object(auto, 'mouse_to_blank'):
        with pytest.raises(userStopError, match='重试 2 次'):
            mirror.search_road()
    assert plan.call_count == 3


def test_entering_through_the_bus_leaves_no_bool_cache():
    mirror_map = road.MirrorMap()
    with patch.object(cfg, 'get_value', side_effect=lambda key, default=None: {'background_click': True}.get(key, default)), \
         patch.object(road, 'search_road_from_road_map', return_value=(True, True)):
        assert mirror_map.get_next_step() is True
    assert mirror_map.floor_map == []
