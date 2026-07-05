@echo off
REM ============================================
REM AI学习教练系统 - Windows 自动同步脚本
REM ============================================

echo [%TIME%] 开始同步...

cd /d "%~dp0"

REM 检查是否在 git 仓库中
if not exist ".git" (
    echo [错误] 未找到 .git 目录，请确认运行目录正确
    pause
    exit /b 1
)

REM 拉取最新代码
git pull origin main 2>nul
if %errorlevel% equ 0 (
    echo [%TIME%] 同步成功
) else (
    echo [%TIME%] 已是最新版本，无需同步
)

echo [%TIME%] 同步完成
exit /b 0
