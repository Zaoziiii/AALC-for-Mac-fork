"""Resize the unique CrossOver game window through macOS Accessibility."""
import time
import ApplicationServices as AX
import Quartz
from AppKit import NSScreen, NSWindow, NSWindowStyleMaskTitled
from module.macos.window import window, require_permissions
from module.macos.geometry import GameGeometry
from module.my_error.my_error import userStopError


def resize_game():
    require_permissions()
    info = window.info()
    bounds = info["kCGWindowBounds"]
    # Resizing must also accept the non-16:9 windows it is intended to repair.
    before = GameGeometry(bounds["X"], bounds["Y"], bounds["Width"], bounds["Height"], 0)
    scale = None
    cx, cy = before.x + before.width / 2, before.y + before.height / 2
    for screen in NSScreen.screens():
        bounds = Quartz.CGDisplayBounds(screen.deviceDescription()["NSScreenNumber"])
        if bounds.origin.x <= cx < bounds.origin.x + bounds.size.width and bounds.origin.y <= cy < bounds.origin.y + bounds.size.height:
            scale = float(screen.backingScaleFactor())
            break
    if scale is None:
        raise userStopError("无法确定游戏所在显示器")
    content = NSWindow.contentRectForFrameRect_styleMask_(((0, 0), (before.width, before.height)), NSWindowStyleMaskTitled)
    titlebar = before.height - content.size.height
    target_width, target_height = 1920 / scale, 1080 / scale + titlebar
    app = AX.AXUIElementCreateApplication(info['kCGWindowOwnerPID'])
    error, windows = AX.AXUIElementCopyAttributeValue(app, AX.kAXWindowsAttribute, None)
    if error:
        raise userStopError(f'无法读取游戏窗口，辅助功能返回 {error}')
    matches = []
    for candidate in windows or []:
        error, title = AX.AXUIElementCopyAttributeValue(candidate, AX.kAXTitleAttribute, None)
        if not error and str(title).replace(' ', '').lower() == 'limbuscompany':
            matches.append(candidate)
    if len(matches) != 1:
        raise userStopError('无法确定唯一的游戏窗口，请退出全屏，使用窗口模式。')
    target = matches[0]
    error, enabled = AX.AXUIElementIsAttributeSettable(target, AX.kAXSizeAttribute, None)
    if error or not enabled:
        raise userStopError('游戏当前不支持调整窗口尺寸，请先退出全屏模式。')
    # The engine uses the 16:9 content below the macOS title bar.
    size = AX.AXValueCreate(AX.kAXValueCGSizeType, (target_width, target_height))
    error = AX.AXUIElementSetAttributeValue(target, AX.kAXSizeAttribute, size)
    if error:
        raise userStopError(f'系统拒绝调整游戏窗口（错误 {error}）。')
    window.last_capture_geometry = None
    window.last_capture_id = None
    for _ in range(20):
        time.sleep(0.1)
        current = window.info()
        bounds = current['kCGWindowBounds']
        if abs(bounds['Width'] - target_width) <= 2 and abs(bounds['Height'] - target_height) <= 2:
            return f'已将游戏画面调整为约 1920×1080 像素（Retina 缩放 {scale:g} 倍）。请点“检测游戏画面”确认画面完整。'
    restored = AX.AXUIElementSetAttributeValue(target, AX.kAXSizeAttribute, AX.AXValueCreate(AX.kAXValueCGSizeType, (before.width, before.height)))
    restore_message = "已请求恢复原窗口尺寸。" if not restored else "恢复原窗口失败，请手动调整。"
    raise userStopError(restore_message + f"窗口未达到目标尺寸，系统实际返回 {bounds['Width']}×{bounds['Height']}（含标题栏）。请把游戏移到能容纳 1920×1080 的显示器，或调整显示缩放后重试。")
