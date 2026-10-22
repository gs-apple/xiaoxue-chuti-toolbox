@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON_EXE="
rem 优先使用 pythonw（无控制台窗口，关闭软件后无任何残留黑窗口）
if exist "%~dp0pythonw.exe" set "PYTHON_EXE=%~dp0pythonw.exe"
if not defined PYTHON_EXE (
    if exist "E:\Program Files (x86)\Python\pythonw.exe" (
        set "PYTHON_EXE=E:\Program Files (x86)\Python\pythonw.exe"
    )
)
if not defined PYTHON_EXE (
    where pythonw >nul 2>nul && set "PYTHON_EXE=pythonw"
)
rem 兜底：只有 python 时（启动瞬间有控制台，但关闭软件后窗口自动退出，不再 pause 卡住）
if not defined PYTHON_EXE (
    if exist "%~dp0python.exe" set "PYTHON_EXE=%~dp0python.exe"
)
if not defined PYTHON_EXE (
    if exist "E:\Program Files (x86)\Python\python.exe" (
        set "PYTHON_EXE=E:\Program Files (x86)\Python\python.exe"
    )
)
if not defined PYTHON_EXE (
    where python >nul 2>nul && set "PYTHON_EXE=python"
)
if not defined PYTHON_EXE (
    echo Python not found. Install Python 3.8+ and add to PATH, or place python.exe in this folder.
    pause
    goto :eof
)

rem 用 start 启动，让本 bat 窗口立即退出；pythonw 不显示控制台，python 关闭软件后控制台自动结束
start "" "%PYTHON_EXE%" main.py
goto :eof
