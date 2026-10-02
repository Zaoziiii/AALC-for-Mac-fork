"""macOS foreground input mapped from the engine's 1920×1080 image space."""
import random
from time import sleep, monotonic
import pyautogui
import pyperclip
from . import AbstractInput
pyautogui.PAUSE = 0.03
from module.macos.window import window
from module.macos.gesture import held_mouse
from module.my_error.my_error import userStopError

class Input(AbstractInput):
    def wait_pause(self):
        from module.macos.control import check_cancelled
        from time import time
        check_cancelled()
        while self.is_pause:
            check_cancelled()
            sleep(0.05)
            self.restore_time = time()

    def _geometry(self):
        self.wait_pause()
        try:
            pyautogui.failSafeCheck()
        except pyautogui.FailSafeException as e:
            raise userStopError('鼠标触及屏幕角落，已停止挂机') from e
        return window.input_geometry()

    def mouse_click(self, x, y, times=1, move_back=False):
        previous=pyautogui.position()
        for _ in range(times):
            point=self._geometry().to_screen(x,y)
            pyautogui.click(*point)
        if move_back:
            pyautogui.moveTo(*previous)
        return True

    def mouse_click_blank(self, coordinate=(32,32), times=1, move_back=False):
        return self.mouse_click(coordinate[0]+random.randint(0,10),coordinate[1]+random.randint(0,10),times,move_back)

    def _drag(self, points, duration, settle, move_back):
        g=self._geometry()
        mapped=[g.to_screen(*p) for p in points]
        previous=pyautogui.position()
        def validate():
            if self.is_pause or window.input_geometry() != g:
                raise userStopError('拖动中断，已释放鼠标')
        pyautogui.moveTo(*mapped[0])
        with held_mouse(pyautogui, validate):
            for start, end in zip(mapped, mapped[1:]):
                start_time=monotonic()
                while True:
                    validate()
                    progress=min(1,(monotonic()-start_time)/max(0.05,duration))
                    pyautogui.moveTo(start[0]+(end[0]-start[0])*progress,
                                     start[1]+(end[1]-start[1])*progress,_pause=False)
                    if progress >= 1:
                        break
                    sleep(0.03)
            deadline=monotonic()+settle
            while monotonic()<deadline:
                validate()
                sleep(0.03)
        if move_back:
            pyautogui.moveTo(*previous)

    def mouse_drag(self,x,y,drag_time=0.1,dx=0,dy=0,move_back=True):
        self._drag([(x,y),(x+dx,y+dy)],drag_time,0.5,move_back)

    def mouse_drag_map(self,x,y,drag_time=0.1,dx=0,dy=0,move_back=True):
        self.mouse_drag(x,y,drag_time,dx,dy,move_back)

    def mouse_swipe_for_scroll(self,x,y,duration=0.3,dx=0,dy=0,move_back=True):
        self._drag([(x,y),(x+dx,y+dy)],duration,0,move_back)

    def mouse_drag_down(self,x,y,reverse=1,move_back=True):
        self.mouse_drag(x,y,0.4,dy=300*reverse,move_back=move_back)

    def mouse_drag_link(self,position,drag_time=0.1,move_back=False):
        if position:
            self._drag(position,drag_time,0,move_back)

    def mouse_scroll(self,direction=-3):
        g = self._geometry()
        # Scrolling over the title bar does not reach the game content.
        pyautogui.moveTo(*g.to_screen(960, 540))
        self._geometry()
        pyautogui.scroll(direction)
        return True

    def mouse_to_blank(self,coordinate=None,move_back=False):
        g = self._geometry()
        previous = pyautogui.position()
        if coordinate is None:
            left, top, right, bottom = g.content_rect
            if not (left <= previous[0] < right and top <= previous[1] < bottom):
                return
            # Clear hover tooltips without repeatedly pulling the pointer to a corner.
            point = (round(g.x + g.width / 2), round(g.y + g.titlebar / 2)) if g.titlebar else g.to_screen(960, 8)
        else:
            point = g.to_screen(*coordinate)
        pyautogui.moveTo(*point)
        if move_back:
            pyautogui.moveTo(*previous)

    def key_press(self,key):
        self._geometry()
        pyautogui.press(key)

    def input_text(self,text):
        self._geometry()
        previous=pyperclip.paste()
        try:
            pyperclip.copy(text)
            # The recipient is a Windows game running in CrossOver.
            pyautogui.hotkey('ctrl','v')
            sleep(0.15)
        finally:
            pyperclip.copy(previous)
