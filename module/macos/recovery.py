"""Relaunch Limbus Company through CrossOver's Steam after the game process exits.

Only used when the game process is really gone (a crash); a minimized or hidden
window still stops the task as before. Logs from the crashed session are saved
first, because the next launch overwrites them.
"""
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from time import monotonic

from module.logger import log
from module.macos.control import wait_cancelled
from module.my_error.my_error import userStopError

STEAM_APP_ID = '1973530'
GAME_EXE = 'LimbusCompany.exe'
GAME_DIR = 'drive_c/Program Files (x86)/Steam/steamapps/common/Limbus Company'
UNITY_LOG_DIR = 'drive_c/users/crossover/AppData/LocalLow/ProjectMoon/LimbusCompany'
BOTTLES = Path.home() / 'Library/Application Support/CrossOver/Bottles'
CROSSOVER_APPS = [Path.home() / 'Applications/CrossOver Preview.app', Path.home() / 'Applications/CrossOver.app',
                  Path('/Applications/CrossOver Preview.app'), Path('/Applications/CrossOver.app')]
WINE_IN_APP = 'Contents/SharedSupport/CrossOver/bin/wine'

WINDOW_TIMEOUT = 300
TITLE_TIMEOUT = 180
MAX_CRASHES = 3
CRASH_WINDOW = 30 * 60


class GameWindowLost(userStopError):
    """The game window is gone; recoverable only if the game process exited."""


def _processes():
    return subprocess.run(['ps', '-axo', 'command'], capture_output=True, text=True).stdout.splitlines()


def game_running():
    return any(GAME_EXE in line and '.exe' in line and 'winewrapper' not in line for line in _processes())


def running_wine():
    """wine of the CrossOver build that is running now, else the first installed one."""
    for line in _processes():
        if '/SharedSupport/CrossOver/' in line and '.app/' in line:
            app = Path(line[:line.index('.app/') + 4])
            if (app / WINE_IN_APP).exists():
                return app / WINE_IN_APP
    for app in CROSSOVER_APPS:
        if (app / WINE_IN_APP).exists():
            return app / WINE_IN_APP
    raise userStopError('未找到 CrossOver，无法自动重启游戏')


def game_bottle():
    for bottle in sorted(BOTTLES.iterdir()) if BOTTLES.exists() else []:
        if (bottle / GAME_DIR / GAME_EXE).exists():
            return bottle
    raise userStopError('未在 CrossOver 瓶子中找到 Limbus Company，无法自动重启游戏')


class GameRecovery:
    def __init__(self):
        self.crashes = []
        # True from the crash until the task thread has taken over the new
        # window; other threads must not act on the old/new window meanwhile.
        self.in_progress = False

    def save_crash_logs(self, bottle, log_root=Path('./logs')):
        target = log_root / f"crash-{datetime.now():%Y%m%d-%H%M%S}"
        target.mkdir(parents=True, exist_ok=True)
        for source in (bottle / GAME_DIR / 'LimbusCompany_d3d11.log', bottle / UNITY_LOG_DIR / 'Player.log'):
            if source.exists():
                shutil.copy2(source, target / source.name)
        log.info(f"已保存崩溃前的游戏日志：{target}")
        return target

    def recover(self):
        """Relaunch the crashed game and wait for its window; raise if it cannot be done.

        in_progress stays set until finish() is called after the task thread
        has re-initialised the new window.
        """
        self.in_progress = True
        try:
            self._recover()
        except BaseException:
            self.in_progress = False
            raise

    def finish(self):
        self.in_progress = False

    def _recover(self):
        from module.macos.window import find_game
        if game_running():
            # The window is hidden or on another desktop, not crashed.
            raise userStopError('游戏窗口不可见但游戏仍在运行，请取消最小化或切回游戏所在桌面后重新开始')
        now = monotonic()
        self.crashes = [t for t in self.crashes if now - t < CRASH_WINDOW] + [now]
        if len(self.crashes) > MAX_CRASHES:
            raise userStopError(f'游戏在 {CRASH_WINDOW // 60} 分钟内崩溃超过 {MAX_CRASHES} 次，已停止自动重启')
        bottle = game_bottle()
        self.save_crash_logs(bottle)
        wine = running_wine()
        log.warning(f"游戏进程已退出，第 {len(self.crashes)} 次自动重启游戏")
        subprocess.Popen([str(wine), '--bottle', bottle.name, '--cx-app',
                          r'C:\Program Files (x86)\Steam\steam.exe', '-applaunch', STEAM_APP_ID],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = monotonic() + WINDOW_TIMEOUT
        while monotonic() < deadline:
            wait_cancelled(5)
            try:
                find_game()
            except userStopError:
                continue
            log.info("游戏窗口已重新出现，等待开场动画结束、进入标题界面")
            self.wait_for_title()
            return
        raise userStopError(f'重启游戏后 {WINDOW_TIMEOUT} 秒内未出现游戏窗口，已停止任务')

    @staticmethod
    def wait_for_title():
        """Watch without input until the title or home screen shows.

        Keys or clicks during the intro could open the quit dialog, and the
        menu-return loop gives up long before a cold start finishes loading.
        """
        from module.automation import auto
        from module.macos.window import window
        deadline = monotonic() + TITLE_TIMEOUT
        while monotonic() < deadline:
            wait_cancelled(3)
            try:
                window.focus()   # new window: reset capture state (never activates in background mode)
                if auto.take_screenshot() is None:
                    continue
            except GameWindowLost:
                continue
            if auto.find_element("base/clear_all_caches_assets.png", model="clam") or auto.find_element("home/window_assets.png"):
                log.info("已到达标题界面，继续返回主界面")
                return
        log.warning(f"{TITLE_TIMEOUT} 秒内未识别到标题界面，仍尝试返回主界面")


game_recovery = GameRecovery()
