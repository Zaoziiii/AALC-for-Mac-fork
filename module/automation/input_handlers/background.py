"""Window-targeted macOS input for the process hosting the CrossOver game.

Events are posted only to the captured game's PID. No clipboard, global event
stream or application activation is used. Mirror map drags alone borrow the
system cursor for their duration (see _drag_borrowing_cursor).
"""
from time import monotonic, sleep as _sleep_uncancellable

import Quartz as Q
from AppKit import NSEvent

from module.logger import log
from module.macos.control import wait_cancelled
from module.macos.focus import focus_guard, user_idle_seconds
from module.macos.window import window
from module.my_error.my_error import userStopError
from .input import Input


USER_IDLE_SECONDS = 1.5


def _inside(point):
    """Clamp a drag point into the 1920x1080 frame, keeping its direction.

    Windows lets a list swipe end outside the window (e.g. in_shop drags a
    gift list from y=363 by -500); here every point must stay on the game.
    """
    return min(max(point[0], 1), 1918), min(max(point[1], 1), 1078)


def _cursor_location():
    return Q.CGEventGetLocation(Q.CGEventCreate(None))


def _user_idle_seconds():
    return user_idle_seconds()


class BackgroundInput(Input):
    # Virtual key codes used by the task engine, not Windows virtual-key codes.
    KEYS = {'p': 35, 'enter': 36, 'return': 36, 'esc': 53, 'escape': 53,
            'left': 123, 'right': 124, 'down': 125, 'up': 126,
            'space': 49, 'tab': 48, 'backspace': 51}

    def __init__(self):
        super().__init__()
        self.source = Q.CGEventSourceCreate(Q.kCGEventSourceStatePrivate)
        focus_guard.is_paused = lambda: self.is_pause

    def _target(self):
        self.wait_pause()
        return window.input_target()

    def _post(self, event, target, release=False):
        if event is None:
            raise userStopError('无法创建后台输入事件')
        if release:
            # Cancellation or movement must not leave a button held. Do not send
            # release to a newly opened game/process if the old one disappeared.
            try:
                info = window.info()
            except userStopError:
                return
            if (info['kCGWindowOwnerPID'], info['kCGWindowNumber']) != (target.pid, target.window_id):
                return
        elif window.input_target() != target:
            raise userStopError('后台输入期间游戏窗口发生变化，请重新开始')
        Q.CGEventSetFlags(event, 0)
        Q.CGEventSetIntegerValueField(event, Q.kCGMouseEventWindowUnderMousePointer, target.window_id)
        Q.CGEventSetIntegerValueField(event, Q.kCGMouseEventWindowUnderMousePointerThatCanHandleThisEvent, target.window_id)
        Q.CGEventPostToPid(target.pid, event)

    def _mouse(self, kind, point, target, release=False, delta=None):
        event = self._mouse_event(kind, point, target)
        if delta is not None:
            Q.CGEventSetIntegerValueField(event, Q.kCGMouseEventDeltaX, round(delta[0]))
            Q.CGEventSetIntegerValueField(event, Q.kCGMouseEventDeltaY, round(delta[1]))
        self._post(event, target, release=release)

    def _mouse_event(self, kind, point, target):
        # NSEvent supplies the actual recipient window number. Quartz's
        # "window under pointer" fields alone do not route a Cocoa event.
        native = NSEvent.mouseEventWithType_location_modifierFlags_timestamp_windowNumber_context_eventNumber_clickCount_pressure_(
            kind, (0, 0), 0, monotonic(), target.window_id, None, 0, 1, 1.0)
        event = Q.CGEventCreateCopy(native.CGEvent())
        Q.CGEventSetSource(event, self.source)
        Q.CGEventSetLocation(event, point)
        return event

    def mouse_click(self, x, y, times=1, move_back=False):
        for _ in range(times):
            target = self._target()
            point = target.geometry.to_screen(x, y)
            self._mouse(Q.kCGEventLeftMouseDown, point, target)
            try:
                wait_cancelled(0.05)
            finally:
                self._mouse(Q.kCGEventLeftMouseUp, point, target, release=True)
            wait_cancelled(0.05)
            focus_guard.note(target.pid, '点击')
        return True

    def _wait_user_idle(self):
        """Borrow the cursor only after the user has left mouse and keyboard alone."""
        logged = False
        while (idle := _user_idle_seconds()) < USER_IDLE_SECONDS:
            if not logged:
                log.info('后台拖动需要暂借鼠标约 1–2 秒，等待鼠标键盘空闲')
                logged = True
            self.wait_pause()
            wait_cancelled(max(0.1, USER_IDLE_SECONDS - idle))

    def _drag(self, points, duration, settle, move_back):
        # Pure background drag. Reliable for battle links and lists; the
        # mirror map camera needs mouse_drag_map instead.
        target = self._target()
        mapped = [target.geometry.to_screen(*_inside(p)) for p in points]
        point = mapped[0]
        self._mouse(Q.kCGEventLeftMouseDown, point, target)
        try:
            # Let Unity process the press before the first drag frame.
            wait_cancelled(0.05)
            for start, end in zip(mapped, mapped[1:]):
                started = monotonic()
                while True:
                    if self.is_pause:
                        raise userStopError('后台拖动已中断并释放鼠标')
                    progress = min(1, (monotonic() - started) / max(0.05, duration))
                    point = (start[0] + (end[0] - start[0]) * progress,
                             start[1] + (end[1] - start[1]) * progress)
                    self._mouse(Q.kCGEventLeftMouseDragged, point, target)
                    if progress >= 1:
                        break
                    wait_cancelled(0.02)
            wait_cancelled(settle)
        finally:
            self._mouse(Q.kCGEventLeftMouseUp, point, target, release=True)
            focus_guard.note(target.pid, '拖动')

    def mouse_drag_map(self, x, y, drag_time=0.1, dx=0, dy=0, move_back=True):
        self._drag_borrowing_cursor([(x, y), (x + dx, y + dy)], drag_time, 0.5)

    def _drag_borrowing_cursor(self, points, duration, settle):
        # The mirror map camera follows Wine's GetCursorPos, which reports the
        # real system cursor, so a PID-only drag jumps toward the user's
        # pointer. The cursor is borrowed for the drag: hardware motion is
        # decoupled, the cursor is warped along the path, then put back.
        self._wait_user_idle()
        target = self._target()
        mapped = [target.geometry.to_screen(*_inside(p)) for p in points]
        point = mapped[0]
        original = _cursor_location()
        Q.CGAssociateMouseAndMouseCursorPosition(False)
        try:
            Q.CGWarpMouseCursorPosition(point)
            wait_cancelled(0.05)
            self._mouse(Q.kCGEventLeftMouseDown, point, target)
            try:
                # Let Unity process the press before the first drag frame.
                wait_cancelled(0.05)
                for start, end in zip(mapped, mapped[1:]):
                    started = monotonic()
                    while True:
                        if self.is_pause:
                            raise userStopError('后台拖动已中断并释放鼠标')
                        progress = min(1, (monotonic() - started) / max(0.05, duration))
                        previous = point
                        point = (start[0] + (end[0] - start[0]) * progress,
                                 start[1] + (end[1] - start[1]) * progress)
                        Q.CGWarpMouseCursorPosition(point)
                        self._mouse(Q.kCGEventLeftMouseDragged, point, target,
                                    delta=(point[0] - previous[0], point[1] - previous[1]))
                        if progress >= 1:
                            break
                        wait_cancelled(0.02)
                wait_cancelled(settle)
            finally:
                self._mouse(Q.kCGEventLeftMouseUp, point, target, release=True)
                # Unity must observe the release before the cursor leaves.
                _sleep_uncancellable(0.15)
        finally:
            Q.CGWarpMouseCursorPosition(original)
            Q.CGAssociateMouseAndMouseCursorPosition(True)
            focus_guard.note(target.pid, '拖动地图')

    def mouse_scroll(self, direction=-3):
        # CrossOver does not reliably deliver background wheel events to Unity.
        # The existing task engine skips wheel-based map zoom in this mode;
        # lists use mouse_swipe_for_scroll instead.
        self._target()
        return False

    def mouse_to_blank(self, coordinate=None, move_back=False):
        # Moving the physical cursor to clear hover would defeat background mode.
        self._target()

    def _key(self, code, text=None):
        target = self._target()
        events = []
        for kind in (Q.kCGEventKeyDown, Q.kCGEventKeyUp):
            native = NSEvent.keyEventWithType_location_modifierFlags_timestamp_windowNumber_context_characters_charactersIgnoringModifiers_isARepeat_keyCode_(
                kind, (0, 0), 0, monotonic(), target.window_id, None, text or '', text or '', False, code)
            event = Q.CGEventCreateCopy(native.CGEvent())
            Q.CGEventSetSource(event, self.source)
            events.append(event)
        down, up = events
        self._post(down, target)
        try:
            wait_cancelled(0.04)
        finally:
            self._post(up, target, release=True)
            focus_guard.note(target.pid, '按键')

    def key_press(self, key):
        if key.lower() not in self.KEYS:
            raise ValueError(f'后台模式不支持的按键：{key}')
        self._key(self.KEYS[key.lower()])

    def input_text(self, text):
        for character in text:
            self._key(0, character)
