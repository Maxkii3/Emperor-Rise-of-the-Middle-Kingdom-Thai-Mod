@echo off
chcp 65001 >nul
echo === Emperor: Rise of the Middle Kingdom - Thai Mod ===
set "GAME=%~1"
if "%GAME%"=="" set /p "GAME=Game folder (e.g. D:\Sierra\Emperor): "
where py >nul 2>nul && (py -3 "%~dp0patcher\install_thai_mod.py" "%GAME%") || (python "%~dp0patcher\install_thai_mod.py" "%GAME%")
pause
