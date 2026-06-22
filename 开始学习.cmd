@echo off
chcp 65001 >nul
title Learn Claude Code - 开始学习
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tutorial-tools\start-tutorial.ps1"
echo.
pause
