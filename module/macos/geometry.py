"""Map the game's normalized image pixels to macOS logical screen points."""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class GameGeometry:
    x: float
    y: float
    width: float
    height: float
    titlebar: float

    @classmethod
    def from_window(cls, x, y, width, height):
        if not all(isfinite(v) for v in (x, y, width, height)) or width < 640:
            raise ValueError('游戏窗口过小或无效，请使用至少 1280×720 的窗口分辨率')
        content_height = width * 9 / 16
        titlebar = height - content_height
        if titlebar < -2 or titlebar > 48:
            raise ValueError('游戏画面必须为 16:9；请在游戏内选择 1280×720 或 1920×1080 窗口模式')
        return cls(x, y, width, height, max(0, titlebar))

    @property
    def content_rect(self):
        return (self.x, self.y + self.titlebar, self.x + self.width, self.y + self.height)

    def to_screen(self, x, y):
        if not (isfinite(x) and isfinite(y) and 0 <= x < 1920 and 0 <= y < 1080):
            raise ValueError(f'拒绝游戏画面外的坐标: {x}, {y}')
        return (round(self.x + x * self.width / 1920),
                round(self.y + self.titlebar + y * (self.height - self.titlebar) / 1080))

    def capture_crop(self, image_size):
        width, height = image_size
        if width <= 0 or height <= 0:
            raise ValueError('游戏截图为空')
        if abs(width / self.width - height / self.height) > 0.05:
            raise ValueError('截图尺寸与窗口不一致，请停止后重试')
        return (0, round(self.titlebar * height / self.height), width, height)


def covers_content(window, rect):
    if window.get('kCGWindowAlpha',1) <= 0:
        return False
    l,t,r,b=rect
    q=window['kCGWindowBounds']
    return max(l,q['X']) < min(r,q['X']+q['Width']) and max(t,q['Y']) < min(b,q['Y']+q['Height'])
