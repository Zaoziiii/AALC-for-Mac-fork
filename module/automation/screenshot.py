from time import monotonic
from module.macos.window import window
from module.logger import log

class ScreenShot:
    @staticmethod
    def take_screenshot(gray=True):
        return window.capture(gray)

    @staticmethod
    def screenshot_benchmark(test_time=10):
        try:
            from module.config import cfg
            window.background = cfg.get_value("win_input_type", "foreground") == "background"
            window.focus()
            start=monotonic()
            for _ in range(test_time):
                window.capture(False)
            return True, (monotonic()-start)*1000/test_time
        except Exception as e:
            log.error(str(e))
            return False, 0.0
