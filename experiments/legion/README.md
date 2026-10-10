# legion 上的入口

legion 上的实验环境是 WSL2 里的 Ubuntu，没有单独的图标。这几个批处理文件放到 Windows 桌面后双击即可：

| 文件 | 作用 |
|---|---|
| `fedguard_shell.bat` | 打开 Ubuntu 终端，并进入项目目录 `/root/innovation` |
| `fedguard_smoke.bat` | 自动实验系统的冒烟测试（约 40 分钟） |
| `fedguard_start.bat` | 启动或继续自动实验循环（每次启动预算 10 小时）；已完成的任务跳过，被中断的训练从最后完成的轮次接着跑 |
| `fedguard_stop.bat` | 优雅停止：当前这一轮训练跑完（约 2 分钟内）后退出，不损失进度 |
| `fedguard_progress.bat` | 查看当前报告、最近的决策和 GPU 状态 |

运行实验的窗口要一直开着。想停就双击 `fedguard_stop.bat`；直接关窗口也可以，只是会损失正在跑的那一轮（约 90 秒），下次启动仍然从断点继续。不用批处理的话，手动方式是：打开 PowerShell，输入 `wsl -d Ubuntu`。
