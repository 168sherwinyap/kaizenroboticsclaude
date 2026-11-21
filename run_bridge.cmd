@echo off
title micro:bit keyboard bridge
cd /d "%~dp0"
python "%~dp0keyboard_bridge.py" %*
pause
