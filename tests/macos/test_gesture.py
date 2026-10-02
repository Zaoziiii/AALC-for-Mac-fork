import unittest
from module.macos.gesture import held_mouse

class Driver:
    FAILSAFE=True
    def __init__(self): self.down=False
    def mouseDown(self, **kwargs): self.down=True
    def mouseUp(self, **kwargs):
        if self.FAILSAFE: raise RuntimeError('corner failsafe')
        self.down=False

class GestureTests(unittest.TestCase):
    def test_release_on_interrupted_drag_even_in_failsafe_corner(self):
        d=Driver()
        with self.assertRaisesRegex(ValueError,'focus lost'):
            with held_mouse(d):
                self.assertTrue(d.down)
                raise ValueError('focus lost')
        self.assertFalse(d.down)
        self.assertTrue(d.FAILSAFE)

class CancellationTests(unittest.TestCase):
    def test_cancel_before_press_never_sends_mouse_down(self):
        d=Driver()
        def cancelled(): raise ValueError('cancelled')
        with self.assertRaisesRegex(ValueError,'cancelled'):
            with held_mouse(d, cancelled):
                pass
        self.assertFalse(d.down)
