@echo off
chcp 65001 >nul
title 音频监控工具 - 环境安装

echo ================================================================
echo    音频监控工具 - 环境检查与依赖安装
echo ================================================================
echo.

:: ========== 检查 Python ==========
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python！
    echo.
    echo 请先安装 Python 3.8 或更高版本
    echo 下载地址：https://www.python.org/downloads/
    echo.
    echo 安装时请务必勾选 "Add Python to PATH"
    echo 安装完成后请重启电脑，然后重新运行此脚本
    echo.
    pause
    exit /b 1
)
python --version
echo [OK] Python 已安装
echo.

:: ========== 检查 .NET ==========
echo [2/5] 检查 .NET 环境...
dotnet --version >nul 2>&1
if errorlevel 1 (
    echo [提示] 未检测到 .NET 8.0
    echo.
    echo 1.3 及以上版本需要 .NET 8.0 运行时才能获取音量数据
    echo 下载地址：https://dotnet.microsoft.com/download/dotnet/8.0
    echo.
    echo 如果不需要音量检测功能，可以忽略此提示
    echo 工具会自动回退到基础检测模式
    echo.
) else (
    dotnet --version
    echo [OK] .NET 已安装
)
echo.

:: ========== 检查 pip ==========
echo [3/5] 检查 pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo [修复] pip 未安装，正在修复...
    python -m ensurepip
)
echo [OK] pip 已就绪
echo.

:: ========== 升级 pip ==========
echo [4/5] 升级 pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip 已更新
echo.

:: ========== 安装依赖库 ==========
echo [5/5] 安装 Python 依赖库...
echo.

echo   > 安装 PySide6 ...
pip install PySide6 --quiet
if errorlevel 1 (
    echo   [失败] PySide6 安装失败
) else (
    echo   [OK] PySide6 安装完成
)

echo   > 安装 psutil ...
pip install psutil --quiet
if errorlevel 1 (
    echo   [失败] psutil 安装失败
) else (
    echo   [OK] psutil 安装完成
)

echo   > 安装 pywin32 ...
pip install pywin32 --quiet
if errorlevel 1 (
    echo   [失败] pywin32 安装失败
) else (
    echo   [OK] pywin32 安装完成
)

echo.

:: ========== 验证安装 ==========
echo ================================================================
echo    安装验证
echo ================================================================
echo.
echo 已安装的 Python 库：
pip list | findstr -i "PySide6 psutil pywin32"
echo.

:: ========== 检查 AudioMeterCOM.exe ==========
if exist "AudioMeterCOM\publish\AudioMeterCOM.exe" (
    echo [OK] AudioMeterCOM.exe 存在
) else (
    echo [提示] AudioMeterCOM.exe 不存在
    echo       请确保该文件在 AudioMeterCOM\publish\ 目录下
    echo       如果不需要音量检测功能，可以忽略
)
echo.

:: ========== 完成 ==========
echo ================================================================
echo    环境配置完成！
echo ================================================================
echo.
echo 下一步：以管理员身份运行主程序
echo   右键 "1.3.7（修复双击失效）.pyw" -> 以管理员身份运行
echo.
echo 提示：如果双击 .pyw 文件无反应，
echo      请右键 -> 打开方式 -> 选择 pythonw.exe
echo.
pause