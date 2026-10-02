from unittest.mock import patch
from module.automation.input_handlers.input import Input
from module.macos.geometry import GameGeometry

def test_parks_in_titlebar_not_top_left():
    driver=Input()
    with patch.object(driver,'_geometry',return_value=GameGeometry(86,26,960,568,28)), patch('pyautogui.position',return_value=(400,300)), patch('pyautogui.moveTo') as move:
        driver.mouse_to_blank()
        move.assert_called_once_with(566,40)

def test_leaves_pointer_outside_content_alone():
    driver=Input()
    with patch.object(driver,'_geometry',return_value=GameGeometry(86,26,960,568,28)), patch('pyautogui.position',return_value=(20,20)), patch('pyautogui.moveTo') as move:
        driver.mouse_to_blank()
        move.assert_not_called()

def test_scroll_targets_game_content():
    driver=Input();events=[]
    with patch.object(driver,'_geometry',return_value=GameGeometry(86,26,960,568,28)), patch('pyautogui.moveTo',side_effect=lambda *p:events.append(('move',p))), patch('pyautogui.scroll',side_effect=lambda n:events.append(('scroll',n))):
        driver.mouse_scroll()
    assert events==[('move',(566,324)),('scroll',-3)]

def test_blank_clicks_stay_clear_of_macos_resize_edges():
    driver=Input()
    geometry=GameGeometry(0,28,960,568,28)
    with patch.object(driver,'_geometry',return_value=geometry), patch('pyautogui.position',return_value=(400,300)), patch('pyautogui.click') as click, patch('module.automation.input_handlers.input.random.randint',return_value=0):
        driver.mouse_click_blank(times=3)
    assert click.call_count==3
    for call in click.call_args_list:
        x,y=call.args
        assert x-geometry.x>=16
        assert y-(geometry.y+geometry.titlebar)>=16
