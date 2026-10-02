"""First-run permissions and non-destructive game screenshot diagnostics."""
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PIL.ImageQt import ImageQt
from module.macos.window import permissions, window

class MacStatusDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('AALC Mac · 权限与游戏检测')
        self.resize(700,300)
        layout=QVBoxLayout(self)
        self.status=QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row=QHBoxLayout()
        for title,anchor in [('屏幕录制设置','Privacy_ScreenCapture'),('辅助功能设置','Privacy_Accessibility')]:
            button=QPushButton(title)
            button.clicked.connect(lambda checked=False,a=anchor: QDesktopServices.openUrl(QUrl('x-apple.systempreferences:com.apple.preference.security?'+a)))
            row.addWidget(button)
        refresh=QPushButton('刷新状态')
        refresh.clicked.connect(self.refresh)
        row.addWidget(refresh)
        layout.addLayout(row)
        self.test=QPushButton('检测游戏画面（不点击、不消耗资源）')
        self.test.clicked.connect(self.capture)
        layout.addWidget(self.test)
        self.resize_button=QPushButton('将游戏窗口调整为 1920×1080')
        self.resize_button.clicked.connect(self.resize_game)
        layout.addWidget(self.resize_button)
        self.preview=QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview)
        self.refresh()

    def refresh(self):
        state=permissions()
        from module.macos.permission_messages import missing_permission_message
        from AppKit import NSBundle
        message = missing_permission_message(state) or '屏幕录制、辅助功能：均已允许。'
        self.status.setText(message + '\n当前应用：' + str(NSBundle.mainBundle().bundlePath()) + '\n先在 CrossOver 启动游戏；使用 16:9 窗口模式。设置中可选 CrossOver 后台模式；游戏可以被遮挡，但不能最小化。')


    def capture(self):
        if not self.task_idle():
            return
        self.test.setEnabled(False)
        self.hide()
        self.parentWidget().hide()
        QTimer.singleShot(500,self._capture)

    def _capture(self):
        try:
            from module.macos.control import reset
            reset()
            from module.config import cfg
            window.background = cfg.get_value("win_input_type", "foreground") == "background"
            window.focus()
            image=window.capture(False)
            self.preview.setPixmap(QPixmap.fromImage(ImageQt(image)).scaled(640,360,Qt.KeepAspectRatio,Qt.SmoothTransformation))
            self.status.setText('已捕获游戏画面并统一为 1920×1080。请确认预览完整、没有标题栏或偏移。\n此检测不会点击游戏，也不代表日常或镜牢已完成实测。')
        except Exception as e:
            self.status.setText(str(e))
        finally:
            self.parentWidget().show()
            self.show()
            self.test.setEnabled(True)

    def resize_game(self):
        if not self.task_idle():
            return
        self.resize_button.setEnabled(False)
        try:
            from module.macos.control import reset
            from module.macos.resize import resize_game
            reset()
            self.status.setText(resize_game())
        except Exception as e:
            self.status.setText(str(e))
        finally:
            self.resize_button.setEnabled(True)

    def task_idle(self):
        task = self.parentWidget().farming_interface.interface_left.my_script
        if task is not None and task.isRunning():
            self.status.setText('请先停止当前任务，再检测画面或调整窗口。')
            return False
        return True
