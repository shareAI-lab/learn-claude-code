@echo off
chcp 65001 >nul
title Learn Claude Code - 关闭教程
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tutorial-tools\stop-tutorial.ps1"
echo.
pause
