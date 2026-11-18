"""Background mode: the game must never take the foreground.

Background input never activates the game on purpose. If the game still
becomes frontmost, the previous app is restored and the step that preceded it
is logged, so the cause can be traced. Pausing the task (Option+P) suspends
this, so the user can take over the game by hand.
"""
from time import monotonic

import Quartz as Q
from AppKit import NSWorkspace

from module.logger import log

def user_idle_seconds():
    # Hardware input only; events posted to the game do not count.
    return Q.CGEventSourceSecondsSinceLastEventType(Q.kCGEventSourceStateHIDSystemState, Q.kCGAnyInputEventType)


ATTRIBUTE_SECONDS = 3.0


class FocusGuard:
    def __init__(self):
        self.previous = None
        self.last_action = None
        self.last_action_at = 0.0
        self.is_paused = lambda: False
        self.restores = 0

    def note(self, game_pid, action):
        """Call after each background input so a later switch can be attributed."""
        self.last_action, self.last_action_at = action, monotonic()
        self.check(game_pid)

    def check(self, game_pid):
        front = NSWorkspace.sharedWorkspace().frontmostApplication()
        if front is None:
            return
        if front.processIdentifier() != game_pid:
            self.previous = front
            return
        if self.is_paused():
            # Paused for manual play: let the game stay in front.
            self.previous = None
            return
        previous = self.previous
        if previous is None or previous.isTerminated():
            return
        if self.last_action and monotonic() - self.last_action_at < ATTRIBUTE_SECONDS:
            cause = f"紧接在{self.last_action}之后"
        else:
            cause = "游戏自行切到前台"
        message = f"游戏被切到前台（{cause}），已切回 {previous.localizedName()}"
        self.restores += 1
        if self.restores == 1:
            # CrossOver raises the game on nearly every background mouse press.
            # It is undone at once; say so once, then keep it to the debug log.
            log.warning(f"{message}。CrossOver 收到后台点击时常会把游戏切到前台，"
                        "AALC 会立刻切回，属正常现象；之后同样的情况只记在调试日志里")
        else:
            log.debug(message)
        previous.activateWithOptions_(0)


focus_guard = FocusGuard()
