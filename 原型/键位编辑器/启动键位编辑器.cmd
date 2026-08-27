@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED_PYTHON%" (
  "%BUNDLED_PYTHON%" serve.py
  goto done
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 serve.py
  goto done
)
where python >nul 2>nul
if not errorlevel 1 (
  python serve.py
  goto done
)
echo 未找到 Python 3，无法启动键位编辑器。
:done
if errorlevel 1 pause
