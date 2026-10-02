from types import SimpleNamespace as NS
from unittest.mock import patch
import pytest
from module.macos import resize
from module.my_error.my_error import userStopError

def test_resize_repairs_non_widescreen_and_verifies_actual_bounds():
    before={'kCGWindowOwnerPID':1,'kCGWindowBounds':{'X':0,'Y':26,'Width':1000,'Height':800}}
    after={'kCGWindowOwnerPID':1,'kCGWindowBounds':{'X':0,'Y':26,'Width':960,'Height':568}}
    screen=NS(deviceDescription=lambda:{'NSScreenNumber':1},backingScaleFactor=lambda:2)
    def get_attribute(obj,key,unused):
        return (0,['game']) if key==resize.AX.kAXWindowsAttribute else (0,'LimbusCompany')
    with patch.object(resize,'require_permissions'), patch.object(resize.window,'info',side_effect=[before,after]), patch.object(resize,'NSScreen',NS(screens=lambda:[screen])), patch.object(resize.Quartz,'CGDisplayBounds',return_value=NS(origin=NS(x=0,y=0),size=NS(width=1147,height=745))), patch.object(resize.AX,'AXUIElementCreateApplication',return_value='app'), patch.object(resize.AX,'AXUIElementCopyAttributeValue',side_effect=get_attribute), patch.object(resize.AX,'AXUIElementIsAttributeSettable',return_value=(0,True)), patch.object(resize.AX,'AXUIElementSetAttributeValue',return_value=0) as set_size, patch.object(resize.time,'sleep'):
        assert '1920×1080' in resize.resize_game()
        assert set_size.call_count==1
        ok, value=resize.AX.AXValueGetValue(set_size.call_args.args[2],resize.AX.kAXValueCGSizeType,None)
        assert ok and value.width==960 and value.height==568
