# AALC Mac · CrossOver 版

面向 **Apple Silicon macOS + CrossOver Steam《边狱公司》**的原生自动化助手。当前版本：**1.0.9-mac.14**。

基于 [KIYI671/AhabAssistantLimbusCompany](https://github.com/KIYI671/AhabAssistantLimbusCompany) 移植，非上游官方 Mac 发行版。保留 Qt 界面、图像/OCR 识别及日常、镜牢任务，替换 Windows 平台控制代码。

## mac.14 主要功能

- **CrossOver 后台操作**：点击和按键定向发送到游戏窗口，可同时使用其他应用。
- **地图拖动修复**：只有镜牢地图拖动短暂借用真实鼠标；等待键鼠空闲 1.5 秒后执行，松手后恢复光标位置。不修改 CrossOver 或游戏，不需要注入动态库或特殊启动器。
- **恢复路线规划**：调整地图后识别节点和连线，规划并缓存路线。问号事件权重最低，结合后续路线总权重择优。
- **游戏意外退出后自动重启**：镜牢流程检测到游戏进程退出时，保存崩溃日志，通过 CrossOver/Steam 重启并尝试继续当前镜牢。30 分钟内超过 3 次退出则停止恢复。
- 修复恩典、初始饰品、主题包楼层、巴士遮挡、明亮战斗界面和队伍名称识别问题。

## 开始使用

1. 打开 **[Releases 下载页面](https://github.com/Zaoziiii/AhabAssistantLimbusCompany/releases/tag/v1.0.9-mac.14)**，在 **Assets** 中下载 **[AALC-Mac-mac.14.zip](https://github.com/Zaoziiii/AhabAssistantLimbusCompany/releases/download/v1.0.9-mac.14/AALC-Mac-mac.14.zip)**，不要下载 Source code 源码包。
2. 解压后将 `AALC Mac.app` 放入“应用程序”，**直接在 macOS 中打开，在 CrossOver 外运行即可**。不需要把 AALC 安装到 CrossOver 容器，也不需要安装 Python；只有 Steam 和《边狱公司》游戏在 CrossOver 中运行。
3. 首次运行请给 AALC Mac 开启“屏幕录制”和“辅助功能”权限，完全退出并重开后使用。

阅读 **[Mac 安装、权限、使用与构建指南](README.macOS.md)**。游戏需使用当前桌面的普通 16:9 窗口；可遮挡，但不能最小化、隐藏、跨桌面或在任务中移动/缩放。

首次使用先通过“权限与游戏检测”检查截图。地图拖动期间鼠标会短暂被借用，后台模式并非全过程零占用鼠标。快捷键：`Ctrl+Q` 停止、`Option+P` 暂停、`Option+R` 恢复。

## 文档

- [Mac 使用指南与常见问题](README.macOS.md)
- [mac.14 更新与验证范围](docs/macos/mac.14.md)
- [平台实现与恢复流程](docs/macos/implementation.md)
- [上游原始文档与素材归属](README.upstream.md)（Windows 操作说明不适用于本分支）

## 验证范围

已有地图拖动、窗口焦点和崩溃重启的局部实机验证记录，已完成整局镜牢及长时间无人值守验收。自动重启不能保证恢复所有崩溃，也不处理游戏进程仍在运行的卡死。

## 许可证与来源

遵循 [AGPL-3.0](LICENSE)，保留上游版权与素材声明。移植基线为上游提交 `ddc22040d1baf3f86fcd94c5384eda038ab8d439`。第三方依赖许可见 [assets/licenses](assets/licenses)。
