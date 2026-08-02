特别感谢 DeepSeek 在开发过程中提供的技术支持

由于 GitHub 文件大小限制，AudioMeterCOM.exe 需要从 Release 附件中单独下载，解压后放到 AudioMeterCOM\publish\ 目录。

# 🎵 音频监控工具 (Audio Monitor Tool)

> 实时监控 Windows 系统中正在使用音频的进程，支持音量检测、进程追踪、快速定位和结束进程。

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)

---

## ✨ 功能特性

- **实时检测**：检测所有正在使用音频的进程，区分用户进程和系统进程
- **音量监测**：显示每个进程的实时音量（dB）
- **进程追踪**：追踪进程的活跃状态、持续时间、消失/恢复间隔
- **颜色标识**：白色（静音）/ 绿色（首次发声）/ 橙色（恢复）/ 灰色（消失）
- **快速操作**：双击复制 PID 并打开任务管理器 / 定位物理文件 / 结束进程
- **日志导出**：导出操作历史为 txt 文件

---

## 🚀 快速开始

### 系统要求

- Windows 10 / Windows 11（64位）
- Python 3.8 或更高版本
- .NET 8.0 Runtime（用于音量检测功能）

### 安装与运行

1. 下载并解压 `audio_tool_1.3.7.zip`
2. 双击运行 `依赖安装.bat` 安装依赖库
3. 右键 `audio_tool_1.3.7.pyw` → 以管理员身份运行

---

## 📦 依赖库

| 库 | 版本 | 用途 |
|---|---|---|
| PySide6 | >= 6.5.0 | GUI 框架 |
| psutil | >= 5.9.0 | 进程管理 |
| pywin32 | >= 306 | Windows API |

---

## 🎨 颜色说明

| 颜色 | 状态 |
|---|---|
| 白色 | 进程存活但静音 |
| 绿色 | 首次发声（从未中断） |
| 橙色 | 恢复（曾静音后恢复发声） |
| 灰色 | 进程已消失/退出 |

---

## 📂 项目结构
audio_tool_1.3.7/
├── audio_tool_1.3.7.pyw # 主程序
├── AudioMeterCOM/
│ └── publish/
│ └── AudioMeterCOM.exe # NAudio COM 检测程序
├── 依赖安装.bat # 一键安装依赖
├── 环境配置说明.txt # 详细配置文档
├── 使用说明.txt # 快速使用指南
└── README.md # 本文件

---

## 🛠️ 技术原理

### 检测方案演进

本工具经历了多次技术迭代：

1. **v1.0**：Windows 内核句柄枚举 + 三重检测（句柄/设备文件/DLL）
2. **v1.3**：NAudio COM 集成，新增音量检测能力
3. **当前版本**：NAudio COM + 内核句柄双重保障

### 核心技术

- `NtQuerySystemInformation`：Windows NT 内核 API，枚举系统句柄
- `NAudio`：C# 音频库，通过 COM 接口获取音频会话
- `PySide6`：Qt for Python，提供界面和交互

---

## ⚠️ 注意事项

- 需要**管理员权限**才能完整检测音频进程
- 结束系统进程可能导致系统不稳定，请谨慎操作
- 橙色是正常状态标识，表示进程曾中断后恢复

---

## 📄 License

MIT License

---

## 🙏 致谢

- [NAudio](https://github.com/naudio/NAudio) - 优秀的 C# 音频库
- [PySide6](https://doc.qt.io/qtforpython/) - Qt for Python
- [psutil](https://github.com/giampaolo/psutil) - 跨平台进程管理
