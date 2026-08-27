@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED_PYTHON%" goto use_bundled
where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if not errorlevel 1 goto use_python
echo 未找到 Python 3，无法启动键位编辑器。
pause
exit /b 1

:use_bundled
"%BUNDLED_PYTHON%" serve.py
goto finish

:use_py
py -3 serve.py
goto finish

:use_python
python serve.py

:finish
if errorlevel 1 pause
