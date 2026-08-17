@echo off
chcp 65001 >nul
title PortGuard 端口进程管家
cd /d "%~dp0"
echo 正在启动 PortGuard ...
echo 用浏览器打开 http://127.0.0.1:8770/
"C:\Users\zzyy\.workbuddy\binaries\python\envs\default\Scripts\python.exe" server.py
pause
