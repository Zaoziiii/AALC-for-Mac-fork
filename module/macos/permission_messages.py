"""Human-readable permission diagnostics, shared by startup and the status UI."""
LABELS = {'screen_recording': '屏幕录制', 'accessibility': '辅助功能'}

def missing_permission_message(state):
    missing = [LABELS[key] for key in LABELS if not state[key]]
    if not missing:
        return None
    allowed = [LABELS[key] for key in LABELS if state[key]]
    message = ('、'.join(allowed) + '已允许。\n') if allowed else ''
    return message + '尚未获得' + '、'.join(missing) + '权限。请在系统设置 → 隐私与安全性 → 对应项目中，添加并开启当前正在运行的 AALC Mac，然后完全退出并重新打开应用。'
