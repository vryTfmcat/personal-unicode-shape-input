@echo off
chcp 65001 >nul
set "BUNDLED_PYTHON=C:\Users\86137\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED_PYTHON%" goto bundled
python "%~dp0serve.py"
if errorlevel 1 pause
goto end
:bundled
"%BUNDLED_PYTHON%" "%~dp0serve.py"
if errorlevel 1 pause
:end
