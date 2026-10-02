# mac.14 平台实现

本分支面向原生 macOS 界面和 CrossOver Steam 游戏，沿用上游任务、OCR 与图像素材，不修改 CrossOver 或游戏二进制。

## 模块边界

- `module/macos/window.py`、`capture.py`、`geometry.py`：窗口查找、截图、Retina/标题栏坐标转换及输入前的窗口校验。
- `module/automation/input_handlers/background.py`：定向事件；`mouse_drag_map` 单独负责借用真实光标。普通后台点击、按键不移动系统指针。
- `module/macos/focus.py`、`control.py`：用户空闲、焦点恢复、暂停/停止和可取消等待。
- `tasks/mirror/search_road.py`：地图调整、节点连线识别、加权路线、缓存方向检查。
- `module/macos/recovery.py`：退出判定、日志归档、CrossOver/容器发现、Steam 重启、窗口/标题等待、频率限制。
- `tasks/base/script_task_scheme.py`：捕获镜牢的 `GameWindowLost`，重启后重新初始化输入和窗口，再进入镜牢流程。
- `tasks/base/retry_monitor.py`：恢复期间让监控线程等待，由主流程接管新窗口。

## 恢复边界

`GameWindowLost → recover() → 游戏进程退出检查 → 保存日志 → Steam 启动 → 等窗口/标题 → init_game() → finish() → 返回主界面 → Mirror.run()`。

游戏仍运行、启动超时或退出频率超限均停止；不通过杀进程处理卡死。恢复期间 `in_progress` 协调主流程与监控线程。配置和日志在应用支持目录，签名包只存放代码与资源。

## 验证

运行 `python -m pytest -q`，测试目录包含后台输入清理、地图识别与路线、窗口几何、权限信息、意外退出恢复和队伍定位。测试不等同于完整镜牢实机验收；发布时分别记录自动测试结果与实机覆盖。
