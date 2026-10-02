from module.macos.permission_messages import missing_permission_message

def test_recording_allowed_only_requests_accessibility():
    message = missing_permission_message({'screen_recording': True, 'accessibility': False})
    assert message.startswith('屏幕录制已允许。')
    assert '尚未获得辅助功能权限' in message
    assert '尚未获得屏幕录制' not in message

def test_both_allowed_has_no_error():
    assert missing_permission_message({'screen_recording': True, 'accessibility': True}) is None

def test_recording_missing_is_named_in_chinese():
    message = missing_permission_message({'screen_recording': False, 'accessibility': True})
    assert '尚未获得屏幕录制权限' in message
