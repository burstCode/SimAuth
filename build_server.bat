@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set VENV=%~dp0.venv
set SERVER=%~dp0server
set DIST=%~dp0dist\SimAuthServer

echo ============================================
echo   SimAuth Server – сборка .exe
echo ============================================
echo.

if not exist "%VENV%\Scripts\python.exe" (
    echo [ОШИБКА] Виртуальное окружение не найдено: %VENV%
    pause & exit /b 1
)

echo [1/3] Сборка сервера через PyInstaller...
cd /d "%SERVER%"
"%VENV%\Scripts\pyinstaller.exe" SimAuthServer.spec --clean --noconfirm
if errorlevel 1 (
    echo [ОШИБКА] PyInstaller завершился с ошибкой
    pause & exit /b 1
)

echo.
echo [2/3] Копирование конфига...
copy /Y "%SERVER%\config.json" "%DIST%\config.json" >nul

echo.
echo [3/3] Готово!
echo.
echo Дистрибутив: %DIST%\
echo   SimAuthServer.exe  – запустить на админском ПК
echo   config.json        – настроить порт, таймаут сессии и т.д.
echo   simauth.db         – создастся автоматически при первом запуске
echo.
pause
