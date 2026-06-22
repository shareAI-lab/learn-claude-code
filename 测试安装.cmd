@echo off
chcp 65001 >nul
title Learn Claude Code - 测试安装
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tutorial-tools\test-installation.ps1"
echo.
pause
