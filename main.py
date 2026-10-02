"""Native Apple Silicon AALC entrypoint."""
import os
import sys
os.environ.pop('SSLKEYLOGFILE', None)
from module.macos.bootstrap import prepare_data_directory
prepare_data_directory()

from PySide6.QtCore import Qt, QTimer, QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
app = QApplication(sys.argv)
app.setApplicationName('AALC Mac')
app.setOrganizationName('AALC Community')
lock = QLockFile(os.path.join(os.getcwd(), 'app.lock'))
if not lock.tryLock(100):
    QMessageBox.information(None, 'AALC Mac', 'AALC Mac 已经在运行。请使用已打开的窗口。')
    sys.exit(0)

try:
    from module.logger.my_log import Logger
    Logger()
    from module.config import cfg
    from module.macos.bootstrap import apply_mac_configuration
    apply_mac_configuration(cfg)
    from app.language_manager import LanguageManager
    manager = LanguageManager()
    language = manager.init_language()
    from app.my_app import MainWindow
    ui = MainWindow([sys.argv[0]])
    QTimer.singleShot(50, lambda: manager.set_language(language))
    from module.logger import log
    log.info('AALC Mac：先通过 CrossOver 启动游戏，选择 16:9 窗口分辨率。需要辅助功能和屏幕录制权限。')
    log.info('设置 → 游戏设置 → 操控方式，可选择 CrossOver 后台模式。Ctrl+Q 停止，Alt+P 暂停。')
    sys.exit(app.exec())
except Exception as exc:
    import traceback
    from pathlib import Path
    Path('startup-error.log').write_text(traceback.format_exc())
    QMessageBox.critical(None, 'AALC Mac 启动失败', f'{exc}\n\n详细信息：{Path.cwd() / "startup-error.log"}')
    sys.exit(1)
