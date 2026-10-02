"""Window discovery and capture. No input is sent from this module."""
import time
from dataclasses import dataclass
import Quartz
from ApplicationServices import AXIsProcessTrusted
from AppKit import NSRunningApplication, NSApplicationActivateIgnoringOtherApps, NSWorkspace
from module.macos.capture import capture_window
from module.macos.geometry import GameGeometry, covers_content
from module.my_error.my_error import userStopError


def permissions():
    return {'screen_recording': bool(Quartz.CGPreflightScreenCaptureAccess()),
            'accessibility': bool(AXIsProcessTrusted())}


def require_permissions():
    from module.macos.control import check_cancelled
    check_cancelled()
    from module.macos.permission_messages import missing_permission_message
    message = missing_permission_message(permissions())
    if message:
        raise userStopError(message)


def windows():
    return list(Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID) or [])


def find_game():
    candidates = [w for w in windows() if w.get('kCGWindowLayer') == 0
                  and str(w.get('kCGWindowName', '')).replace(' ', '').lower() == 'limbuscompany'
                  and w['kCGWindowBounds']['Width'] >= 640]
    if not candidates:
        from module.macos.recovery import GameWindowLost
        raise GameWindowLost('当前桌面未找到 Limbus Company 游戏窗口。后台模式允许其他普通窗口遮挡；请确认游戏未最小化或隐藏，且未切到全屏应用或其他桌面。')
    if len(candidates) > 1:
        raise userStopError(f'检测到 {len(candidates)} 个 Limbus Company 游戏窗口，无法确定目标，请只保留一个游戏窗口。')
    return candidates[0]


@dataclass(frozen=True)
class InputTarget:
    pid: int
    window_id: int
    geometry: GameGeometry


class GameWindow:
    def __init__(self):
        self.background = False
        self.last_capture_geometry = None
        self.last_capture_id = None
        self.last_capture_pid = None

    def info(self):
        return find_game()

    @staticmethod
    def geometry(info):
        b = info['kCGWindowBounds']
        try:
            return GameGeometry.from_window(b['X'], b['Y'], b['Width'], b['Height'])
        except ValueError as e:
            raise userStopError(str(e)) from e

    def focus(self):
        require_permissions()
        info = self.info()
        if not self.background:
            app = NSRunningApplication.runningApplicationWithProcessIdentifier_(info['kCGWindowOwnerPID'])
            if app is None or not app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps):
                raise userStopError('无法激活游戏，请点击游戏窗口后重新开始')
            time.sleep(0.3)
        self.last_capture_geometry = None
        self.last_capture_id = None
        self.last_capture_pid = None

    def assert_front(self, info):
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None or app.processIdentifier() != info['kCGWindowOwnerPID']:
            raise userStopError('游戏已失去焦点，已停止输入。请回到游戏后重新开始。')
        # Reject any normal window covering the game, including another Wine window.
        g = self.geometry(info)
        l,t,r,b = g.content_rect
        for w in windows():
            if w['kCGWindowNumber'] == info['kCGWindowNumber']:
                return
            if covers_content(w, g.content_rect):
                raise userStopError('游戏窗口被其他窗口遮挡，已停止输入。请移开遮挡窗口后重新开始。')
        raise userStopError('游戏窗口已消失，已停止输入')

    def capture(self, gray=True):
        require_permissions()
        info = self.info()
        if not self.background:
            self.assert_front(info)
        g = self.geometry(info)
        if self.last_capture_geometry is not None and (g != self.last_capture_geometry or info['kCGWindowNumber'] != self.last_capture_id or info['kCGWindowOwnerPID'] != self.last_capture_pid):
            raise userStopError('游戏窗口位置或大小已改变，请重新开始')
        # Native capture excludes shadows; Retina pixels are normalized below.
        raw = capture_window(int(info['kCGWindowNumber']))
        current = self.info()
        if current['kCGWindowNumber'] != info['kCGWindowNumber'] or current['kCGWindowOwnerPID'] != info['kCGWindowOwnerPID'] or self.geometry(current) != g:
            raise userStopError('截图期间游戏窗口发生变化，请重新开始')
        image = raw.crop(g.capture_crop(raw.size)).convert('RGB').resize((1920,1080))
        self.last_capture_geometry = g
        self.last_capture_id = info['kCGWindowNumber']
        self.last_capture_pid = info['kCGWindowOwnerPID']
        if self.background:
            from module.macos.focus import focus_guard
            focus_guard.check(int(info['kCGWindowOwnerPID']))
        return image.convert('L') if gray else image

    def input_geometry(self):
        return self.input_target().geometry

    def input_target(self):
        require_permissions()
        info = self.info()
        if not self.background:
            self.assert_front(info)
        g = self.geometry(info)
        if self.last_capture_geometry is None:
            raise userStopError('尚未获取游戏画面，拒绝发送输入')
        if self.last_capture_id != info['kCGWindowNumber'] or self.last_capture_pid != info['kCGWindowOwnerPID'] or g != self.last_capture_geometry:
            raise userStopError(f'游戏窗口位置或大小已改变，已停止输入。截图时: {self.last_capture_geometry}, 窗口ID={self.last_capture_id}；当前: {g}, 窗口ID={info["kCGWindowNumber"]}。请重新调整窗口后开始。')
        return InputTarget(int(info['kCGWindowOwnerPID']), int(info['kCGWindowNumber']), g)

window = GameWindow()
