@echo off
chcp 65001 >nul
title 音频监控工具 - 依赖安装

echo ================================================================
echo    音频监控工具 - 依赖库一键安装
echo ================================================================
echo.

:: 检查 Python 是否安装
echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python！
    echo.
    echo 请先安装 Python 3.8 或更高版本
    echo 下载地址：https://www.python.org/downloads/
    echo.
    echo 安装时请务必勾选 "Add Python to PATH"
    pause
    exit /b 1
)

python --version
echo.

:: 检查 pip
echo [2/4] 检查 pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo [错误] pip 未安装，正在修复...
    python -m ensurepip
)
echo.

:: 升级 pip
echo [3/4] 升级 pip...
python -m pip install --upgrade pip
echo.

:: 安装依赖库
echo [4/4] 安装依赖库...
echo.

echo 正在安装 PySide6（GUI框架）...
pip install PySide6
if errorlevel 1 (
    echo [警告] PySide6 安装失败，请检查网络连接后重试
)

echo.
echo 正在安装 psutil（进程管理）...
pip install psutil

echo.
echo 正在安装 pywin32（Windows API）...
pip install pywin32

echo.
echo ================================================================
echo    安装完成！
echo ================================================================
echo.
echo 已安装的库：
pip list | findstr -i "PySide6 psutil pywin32"
echo.
echo 如果所有库都显示版本号，说明安装成功！
echo.
echo 接下来请以管理员身份运行主程序：
echo   右键 "1.3.7（修复双击失效）.pyw" -> 以管理员身份运行
echo.
pause