@echo off
chcp 65001 >nul
title PortGuard 端口进程管家（管理员）
cd /d "%~dp0"
echo 正在以管理员身份启动 PortGuard ...
powershell -Command "Start-Process 'C:\Users\zzyy\.workbuddy\binaries\python\envs\default\Scripts\python.exe' -ArgumentList 'server.py' -Verb runAs -WindowStyle Normal"
