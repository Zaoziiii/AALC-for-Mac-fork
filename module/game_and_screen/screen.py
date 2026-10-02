"""macOS game window facade used by the existing task engine."""
from module.macos.window import window, find_game

class Handle:
    def init_handle(self, *args):
        return self.hwnd

    @property
    def hwnd(self):
        try:
            return int(find_game()['kCGWindowNumber'])
        except Exception:
            return 0

    def rect(self, client=False):
        g = window.geometry(window.info())
        return g.content_rect if client else (g.x,g.y,g.x+g.width,g.y+g.height)

    def width(self, client=False):
        r=self.rect(client)
        return r[2]-r[0]

    def height(self, client=False):
        r=self.rect(client)
        return r[3]-r[1]

class Screen:
    def __init__(self, title, game):
        self.title, self.game, self.handle = title, game, Handle()

    def init_handle(self):
        window.info()
        return True

    def set_win(self):
        window.focus()
        window.capture(False)

    def reset_win(self, activate=False):
        # The macOS edition never alters the user's window style or dimensions.
        if activate:
            window.focus()
