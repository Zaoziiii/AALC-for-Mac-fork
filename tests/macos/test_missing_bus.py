from unittest.mock import patch
import pytest
from module.automation import auto
from module.my_error.my_error import userStopError
from tasks.mirror.search_road import search_road_from_road_map


def test_lost_bus_after_drag_stops_without_blind_navigation():
    with patch.object(auto, 'click_element', return_value=False), patch.object(auto, 'find_element', side_effect=[(704,396), None, None]), patch.object(auto, 'get_restore_time', return_value=None), patch.object(auto, 'mouse_drag_map'), patch.object(auto, 'mouse_to_blank'), patch('tasks.mirror.search_road.sleep'), patch('tasks.base.retry.check_times', return_value=False):
        with pytest.raises(userStopError, match='巴士'):
            search_road_from_road_map()
