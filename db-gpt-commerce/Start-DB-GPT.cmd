@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-DB-GPT.ps1"
if errorlevel 1 (pause) else (start "" "http://127.0.0.1:5670")
