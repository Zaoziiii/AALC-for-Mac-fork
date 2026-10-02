import unittest

class GeometryTests(unittest.TestCase):
    def setUp(self):
        from module.macos.geometry import GameGeometry
        self.geometry = GameGeometry

    def test_titlebar_is_excluded_and_center_maps_to_logical_points(self):
        g = self.geometry.from_window(100, 50, 1280, 745)
        self.assertEqual(g.content_rect, (100, 75, 1380, 795))
        self.assertEqual(g.to_screen(960, 540), (740, 435))

    def test_fullscreen_has_no_titlebar(self):
        g = self.geometry.from_window(0, 0, 1920, 1080)
        self.assertEqual(g.content_rect, (0, 0, 1920, 1080))
        self.assertEqual(g.to_screen(1919, 1079), (1919, 1079))

    def test_retina_capture_crop_uses_image_scale(self):
        g = self.geometry.from_window(100, 50, 1280, 745)
        self.assertEqual(g.capture_crop((2560, 1490)), (0, 50, 2560, 1490))

    def test_window_on_second_display_keeps_negative_coordinates(self):
        g = self.geometry.from_window(-1280, 25, 1280, 745)
        self.assertEqual(g.to_screen(960, 540), (-640, 410))

    def test_wrong_aspect_or_tiny_window_is_rejected(self):
        for bounds in [(0,0,0,0), (0,0,1920,1500), (0,0,100,80), (0,0,1920,900)]:
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                self.geometry.from_window(*bounds)

    def test_input_outside_content_is_rejected(self):
        g = self.geometry.from_window(0,0,1280,745)
        for point in [(-1,10), (1920,10), (10,1080), (float('nan'),5)]:
            with self.subTest(point=point), self.assertRaises(ValueError):
                g.to_screen(*point)

if __name__ == '__main__':
    unittest.main()

class OcclusionTests(unittest.TestCase):
    def test_floating_window_is_an_occluder(self):
        from module.macos.geometry import covers_content
        overlay={'kCGWindowLayer':3,'kCGWindowAlpha':1,'kCGWindowBounds':{'X':200,'Y':100,'Width':50,'Height':50}}
        self.assertTrue(covers_content(overlay,(0,25,1280,745)))
        self.assertFalse(covers_content(overlay,(400,25,1680,745)))
        overlay['kCGWindowAlpha']=0
        self.assertFalse(covers_content(overlay,(0,25,1280,745)))
