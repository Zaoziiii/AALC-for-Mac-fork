import datetime

from PySide6.QtCore import QT_TRANSLATE_NOOP, QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QSizePolicy,
    QWidget,
)
from qfluentwidgets import (
    ExpandLayout,
    InfoBarPosition,
    ScrollArea,
    SmoothMode,
    Theme,
    isDarkTheme,
    qconfig,
    setTheme,
)
from qfluentwidgets import FluentIcon as FIF

from app import win_input_type_options
from app.base_combination import (
    BasePrimaryPushSettingCard,
    BasePushSettingCard,
    BaseSettingCardGroup,
    ComboBoxSettingCard,
    HotkeySettingCard,
    PushSettingCardChance,
    PushSettingCardDate,
    PushSettingCardText,
    SwitchSettingCard,
)
from app.card.messagebox_custom import BaseInfoBar
from app.common.ui_config import get_setting_interface_qss
from app.language_manager import SUPPORTED_LANG_NAME, LanguageManager
from app.theme_pack_setting_interface import ThemePackSettingDialog
from app.widget.setting_nav import SettingNav
from module.config import cfg, theme_list
from utils.adb_endpoint import normalize_adb_host


class SettingInterface(QWidget):
    # 手动检查图片资源更新请求，由主窗口统一接管后续流程。
    manualResourceSyncRequested = Signal()

    def __init__(self, parent=None):
        """初始化设置页及其资源同步入口。

        参数:
            parent: Qt 父对象。
        """
        super().__init__(parent=parent)
        # 先创建基础界面骨架、卡片和导航结构。
        self.__init_widget()
        self.__init_card()
        self.__initLayout()
        self.setting_nav.add_nav_items([
            ("game", "游戏设置", self.game_setting_group),
            ("theme_pack", "镜牢主题包", self.theme_pack_group),
            ("game_path", "启动与显示", self.game_path_group),
            ("personal", "个性化", self.personal_group),
            ("logs", "日志设置", self.logs_group),
            ("about", "关于", self.about_group),
            ("experimental", "实验性", self.experimental_group),
        ])
        self.setting_nav.navClicked.connect(self.__on_nav_clicked)
        self.content_scroll.verticalScrollBar().valueChanged.connect(self.__on_content_scrolled)

        # 再应用主题样式并注册主题切换监听。
        self._apply_theme_style()
        qconfig.themeChanged.connect(self._apply_theme_style)

        # 最后连接交互信号并注册到语言管理器。
        self.__connect_signal()
        self.setObjectName("SettingInterface")

        LanguageManager().register_component(self)

    def __init_widget(self):
        # main container
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # left navigation frame
        self.setting_nav = SettingNav(self)

        # right scroll area with existing content
        self.content_scroll = ScrollArea(self)
        self.content_scroll.setObjectName("contentScroll")
        self.content_scroll.setSmoothMode(SmoothMode.LINEAR, Qt.Orientation.Vertical)
        self.content_scroll.scrollDelagate.verticalSmoothScroll.duration = 100
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_scroll.enableTransparentBackground()

        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("scrollWidget")
        self.expand_layout = ExpandLayout(self.scroll_widget)
        self.content_scroll.setWidget(self.scroll_widget)

        # assemble
        self.main_layout.addWidget(self.setting_nav)
        self.main_layout.addWidget(self.content_scroll)
        self.main_layout.setStretch(0, 0)
        self.main_layout.setStretch(1, 1)

        # give nav a fixed width and prevent stretch
        self.setting_nav.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.content_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def __init_card(self):
        """初始化设置页中全部设置卡片。"""
        # 第一组：创建游戏、模拟器、启动方式等基础设置卡片。
        self.game_setting_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "游戏设置"), self.scroll_widget
        )
        self.game_setting_card = ComboBoxSettingCard(
            "select_team_by_order",
            FIF.SEARCH,
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", "选择队伍方式"),
            QT_TRANSLATE_NOOP(
                "ComboBoxSettingCard",
                "使用队伍名为识别“TEAMS#XX”/“编队#XX”的队伍，使用序号为使用从上到下第X个队伍",
            ),
            texts={
                QT_TRANSLATE_NOOP("ComboBoxSettingCard", "使用队伍名"): False,
                QT_TRANSLATE_NOOP("ComboBoxSettingCard", "使用队伍序号"): True,
            },
            parent=self.game_setting_group,
        )
        self.auto_hard_mirror_card = SwitchSettingCard(
            FIF.PLAY,
            QT_TRANSLATE_NOOP("SwitchSettingCard", "自动困难模式"),
            QT_TRANSLATE_NOOP(
                "SwitchSettingCard",
                "每周自动将前三场镜牢设置为困难模式执行，请确认启用了“困牢单次加成”功能",
            ),
            "auto_hard_mirror",
            parent=self.game_setting_group,
        )
        self.last_auto_hard_mirror_card = PushSettingCardDate(
            QT_TRANSLATE_NOOP("PushSettingCardDate", "修改"),
            FIF.DATE_TIME,
            QT_TRANSLATE_NOOP("PushSettingCardDate", "上次自动切换困难镜牢的时间戳"),
            "last_auto_change",
        )
        self.hard_mirror_chance_card = PushSettingCardChance(
            QT_TRANSLATE_NOOP("PushSettingCardChance", "修改"),
            FIF.UNIT,
            QT_TRANSLATE_NOOP("PushSettingCardChance", "困难模式剩余次数"),
            config_name="hard_mirror_chance",
            max_value=3,
            content=QT_TRANSLATE_NOOP("PushSettingCardChance", "第一次运行请手动设定，之后将自动修改"),
            on_confirm=self._on_hard_mirror_chance_confirm,
        )
        self.win_input_type_card = ComboBoxSettingCard(
            "win_input_type",
            FIF.CONNECT,
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", "操控方式"),
            "后台模式允许遮挡游戏窗口，但不能最小化或移动、缩放窗口。镜牢自动使用方向键，按可见路线逐步寻路，不拖动地图；不支持后台滚轮。更改后下次开始任务生效。",
            texts=win_input_type_options,
            parent=self.game_setting_group,
        )
        self.screenshot_benchmark_card = BasePrimaryPushSettingCard(
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "截图测试"),
            FIF.CAMERA,
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "截图性能测试"),
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "测试截图功能的性能"),
            parent=self.game_setting_group,
        )


        self.game_path_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "启动游戏"), self.scroll_widget
        )
        self.minimize_to_tray_card = SwitchSettingCard(
            FIF.REMOVE,
            QT_TRANSLATE_NOOP("SwitchSettingCard", "最小化到托盘"),
            QT_TRANSLATE_NOOP(
                "SwitchSettingCard",
                "开启后，最小化时将隐藏到系统托盘",
            ),
            "minimize_to_tray",
            parent=self.game_path_group,
        )

        self.personal_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "个性化"), self.scroll_widget
        )
        self.language_card = ComboBoxSettingCard(
            "language_in_program",
            FIF.LANGUAGE,
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", "语言"),
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", "设置程序 UI 使用的语言"),
            texts=SUPPORTED_LANG_NAME,
            parent=self.personal_group,
        )
        self.theme_card = ComboBoxSettingCard(
            "theme_mode",
            FIF.BRUSH,
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", "应用主题"),
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", "调整应用的主题外观"),
            texts={
                QT_TRANSLATE_NOOP("ComboBoxSettingCard", "跟随系统"): "AUTO",
                QT_TRANSLATE_NOOP("ComboBoxSettingCard", "亮色模式"): "LIGHT",
                QT_TRANSLATE_NOOP("ComboBoxSettingCard", "深色模式"): "DARK",
            },
            parent=self.personal_group,
        )
        self.zoom_card = ComboBoxSettingCard(
            "zoom_scale",
            FIF.ZOOM,
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", "缩放"),
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", "设置程序 UI 使用的缩放"),
            texts={
                QT_TRANSLATE_NOOP("ComboBoxSettingCard", "跟随系统"): 0,
                "50%": 50,
                "75%": 75,
                "90%": 90,
                "100%": 100,
                "125%": 125,
                "150%": 150,
                "175%": 175,
                "200%": 200,
            },
            parent=self.personal_group,
        )
        self.hotkey_card = HotkeySettingCard(
            QT_TRANSLATE_NOOP("BasePushSettingCard", "修改"),
            FIF.EDIT,
            QT_TRANSLATE_NOOP("BasePushSettingCard", "快捷键设置"),
            {
                QT_TRANSLATE_NOOP("BasePushSettingCard", "结束运行的脚本"): "shutdown_hotkey",
                QT_TRANSLATE_NOOP("BasePushSettingCard", "暂停脚本运行"): "pause_hotkey",
                QT_TRANSLATE_NOOP("BasePushSettingCard", "恢复脚本运行"): "resume_hotkey",
            },
            parent=self.personal_group,
        )

        # 资源同步相关卡片集中放在更新设置分组下，便于用户理解它与软件更新的关系。

        # 最后一组：创建日志、关于和实验性功能等辅助设置卡片。
        self.logs_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "日志设置"), self.scroll_widget
        )
        self.open_logs_card = BasePrimaryPushSettingCard(
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "日志"),
            FIF.FOLDER_ADD,
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "打开日志文件夹"),
            parent=self.logs_group,
        )

        self.about_group = BaseSettingCardGroup(QT_TRANSLATE_NOOP("BaseSettingCardGroup", "关于"), self.scroll_widget)
        self.github_card = BasePrimaryPushSettingCard(
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "项目主页"),
            FIF.GITHUB,
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "项目主页"),
            "https://github.com/KIYI671/AhabAssistantLimbusCompany",
        )
        self.discord_group_card = BasePrimaryPushSettingCard(
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "加入群聊"),
            FIF.EXPRESSIVE_INPUT_ENTRY,
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "discord群"),
            "https://discord.gg/vUAw98cEVe",
        )
        self.feedback_card = BasePrimaryPushSettingCard(
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "提供反馈"),
            FIF.FEEDBACK,
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "提供反馈"),
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "帮助我们改进 AhabAssistantLimbusCompany"),
        )

        self.theme_pack_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "镜牢主题包设置"),
            self.scroll_widget,
        )
        self.theme_pack_card = BasePrimaryPushSettingCard(
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "配置"),
            FIF.LIBRARY,
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", "主题包权重配置"),
            QT_TRANSLATE_NOOP(
                "BasePrimaryPushSettingCard",
                "配置镜牢主题包的选择优先级权重",
            ),
            parent=self.theme_pack_group,
        )

        self.experimental_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "实验性内容"), self.scroll_widget
        )

        self.keep_screen_awake_card = SwitchSettingCard(
            FIF.VIEW,
            QT_TRANSLATE_NOOP("SwitchSettingCard", "运行时保持屏幕唤醒"),
            QT_TRANSLATE_NOOP(
                "SwitchSettingCard",
                "任务运行中阻止系统休眠与锁屏；任务结束、停止或异常退出后会自动恢复系统默认策略",
            ),
            config_name="experimental_keep_screen_awake",
            parent=self.experimental_group,
        )

    def _on_hard_mirror_chance_confirm(self, _: int) -> None:
        """手动调整困难模式次数后，同步刷新自动切换时间戳。

        参数:
            _: PushSettingCardChance 传入的确认值，此处不需要直接使用。
        """
        # 记录当前时间为新的自动切换时间戳。
        now = datetime.datetime.now()
        cfg.set_value("last_auto_change", now.timestamp())
        cfg.flush()
        # 同步刷新卡片上的缓存值和显示文本。
        self.last_auto_hard_mirror_card.config_value = now
        self.last_auto_hard_mirror_card.contentLabel.setText(now.strftime("%Y-%m-%d %H:%M"))

    def __initLayout(self):
        """将已创建的设置卡片挂载到各自分组与滚动布局中。"""
        # 先把卡片加入各自的设置分组。
        self.game_setting_group.addSettingCard(self.game_setting_card)
        self.game_setting_group.addSettingCard(self.auto_hard_mirror_card)
        self.game_setting_group.addSettingCard(self.last_auto_hard_mirror_card)
        self.game_setting_group.addSettingCard(self.hard_mirror_chance_card)
        self.game_setting_group.addSettingCard(self.win_input_type_card)
        self.game_setting_group.addSettingCard(self.screenshot_benchmark_card)

        self.theme_pack_group.addSettingCard(self.theme_pack_card)


        self.game_path_group.addSettingCard(self.minimize_to_tray_card)


        self.personal_group.addSettingCard(self.language_card)
        self.personal_group.addSettingCard(self.theme_card)
        self.personal_group.addSettingCard(self.zoom_card)
        self.personal_group.addSettingCard(self.hotkey_card)


        self.logs_group.addSettingCard(self.open_logs_card)

        self.about_group.addSettingCard(self.github_card)
        self.about_group.addSettingCard(self.discord_group_card)
        self.about_group.addSettingCard(self.feedback_card)

        self.experimental_group.addSettingCard(self.keep_screen_awake_card)

        # 再把各个分组按页面顺序加入主滚动布局。
        self.expand_layout.addWidget(self.game_setting_group)
        self.expand_layout.addWidget(self.theme_pack_group)
        self.expand_layout.addWidget(self.game_path_group)
        self.expand_layout.addWidget(self.personal_group)
        self.expand_layout.addWidget(self.logs_group)
        self.expand_layout.addWidget(self.about_group)
        self.expand_layout.addWidget(self.experimental_group)



    def __on_nav_clicked(self, key: str, widget):
        """导航栏点击，滚动到指定内容"""
        target_y = widget.mapTo(self.scroll_widget, QPoint(0, 0)).y()
        bar = self.content_scroll.verticalScrollBar()
        # Offset to prevent the card from sticking exactly to the top edge
        SCROLL_OFFSET_PX = 8
        bar.setValue(max(0, target_y - SCROLL_OFFSET_PX))

    def __on_content_scrolled(self, value: int):
        """内容区域滚动，同步高亮导航栏"""
        self.setting_nav.process_content_scrolled(value, self.scroll_widget)

    def _apply_theme_style(self, *_):
        light_qss, dark_qss = get_setting_interface_qss()
        self.setStyleSheet(dark_qss if isDarkTheme() else light_qss)

    def __connect_signal(self):
        """连接设置页卡片与处理函数之间的信号。"""
        # 先连接按钮点击类交互，包括图片资源手动检查入口。
        self.open_logs_card.clicked.connect(self.__onOpenLogsCardClicked)
        self.screenshot_benchmark_card.clicked.connect(self.__onScreenshotBenchmarkCardClicked)
        self.theme_pack_card.clicked.connect(self.__onThemePackCardClicked)

        # 再连接配置变更类交互，保证界面动作能同步刷新配置和主题。
        self.zoom_card.valueChanged.connect(self.__onZoomCardValueChanged)
        self.theme_card.valueChanged.connect(self.__onThemeCardChanged)

        # 最后连接外链卡片，统一复用打开 URL 的回调工厂。
        self.github_card.clicked.connect(self.__openUrl("https://github.com/KIYI671/AhabAssistantLimbusCompany"))
        self.discord_group_card.clicked.connect(self.__openUrl("https://discord.gg/vUAw98cEVe"))
        self.feedback_card.clicked.connect(
            self.__openUrl("https://github.com/KIYI671/AhabAssistantLimbusCompany/issues")
        )





    def __onOpenLogsCardClicked(self):
        import os

        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath("./logs")))

    def __onScreenshotBenchmarkCardClicked(self):
        from module.automation.screenshot import ScreenShot

        flag, time = ScreenShot.screenshot_benchmark()
        if flag:
            msg = QT_TRANSLATE_NOOP("BaseInfoBar", "10次截图平均耗时 {time:.2f} ms")
            BaseInfoBar.success(
                title=QT_TRANSLATE_NOOP("BaseInfoBar", "截图测试结束"),
                content=msg,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self,
                content_kwargs={"time": time},
            )
        else:
            msg = QT_TRANSLATE_NOOP("BaseInfoBar", "请确保LimbusCompany正在运行")
            BaseInfoBar.error(
                title=QT_TRANSLATE_NOOP("BaseInfoBar", "截图测试结束"),
                content=msg,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self,
            )





    def __onZoomCardValueChanged(self):
        bar = BaseInfoBar.success(
            title=QT_TRANSLATE_NOOP("BaseInfoBar", "更改将在重新启动后生效"),
            content="",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=5000,
            parent=self,
        )



    def __openUrl(self, url):
        return lambda: QDesktopServices.openUrl(QUrl(url))

    def __onThemePackCardClicked(self):
        """打开主题包权重配置对话框"""
        dialog = ThemePackSettingDialog(
            self,
            config_data=theme_list.config,
            save_path=theme_list.theme_pack_list_path,
        )
        dialog.exec()

    def retranslateUi(self):
        self.setting_nav.retranslateUi()

        self.game_setting_group.retranslateUi()
        self.game_setting_card.retranslateUi()
        self.auto_hard_mirror_card.retranslateUi()
        self.last_auto_hard_mirror_card.retranslateUi()
        self.hard_mirror_chance_card.retranslateUi()
        self.win_input_type_card.retranslateUi()
        self.minimize_to_tray_card.retranslateUi()
        self.screenshot_benchmark_card.retranslateUi()
        self.theme_pack_group.retranslateUi()
        self.theme_pack_card.retranslateUi()
        self.game_path_group.retranslateUi()
        self.personal_group.retranslateUi()
        self.language_card.retranslateUi()
        self.theme_card.retranslateUi()
        self.zoom_card.retranslateUi()
        self.hotkey_card.retranslateUi()
        self.logs_group.retranslateUi()
        self.about_group.retranslateUi()
        self.open_logs_card.retranslateUi()
        self.github_card.retranslateUi()
        self.discord_group_card.retranslateUi()
        self.feedback_card.retranslateUi()
        self.experimental_group.retranslateUi()
        self.keep_screen_awake_card.retranslateUi()

    def __onThemeCardChanged(self):
        theme_mode = cfg.get_value("theme_mode")
        if theme_mode == "AUTO":
            setTheme(Theme.AUTO)
        elif theme_mode == "LIGHT":
            setTheme(Theme.LIGHT)
        elif theme_mode == "DARK":
            setTheme(Theme.DARK)
