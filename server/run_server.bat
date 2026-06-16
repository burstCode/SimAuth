@echo off
cd /d "%~dp0"

:: Ищем Python: сначала venv рядом с репо, потом системный
set PYTHON=
if exist "%~dp0..\.venv\Scripts\python.exe" (
    set PYTHON=%~dp0..\.venv\Scripts\python.exe
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set PYTHON=%~dp0.venv\Scripts\python.exe
) else (
    where python >nul 2>&1
    if not errorlevel 1 set PYTHON=python
)

if "%PYTHON%"=="" (
    echo [ОШИБКА] Python не найден.
    echo Установи Python 3.11+ или положи .venv рядом с папкой SimAuth.
    pause & exit /b 1
)

echo SimAuth Server запускается...
echo Адрес: http://localhost:8000
echo Ctrl+C — остановить
echo.
"%PYTHON%" main.py
pause
