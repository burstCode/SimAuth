@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set VENV=%~dp0.venv
set AGENT=%~dp0agent
set DIST=%~dp0dist\SimAuthAgent

echo ============================================
echo   SimAuth Agent – сборка .exe
echo ============================================
echo.

:: Проверяем venv
if not exist "%VENV%\Scripts\python.exe" (
    echo [ОШИБКА] Виртуальное окружение не найдено: %VENV%
    pause & exit /b 1
)

echo [1/3] Сборка агента через PyInstaller...
cd /d "%AGENT%"
"%VENV%\Scripts\pyinstaller.exe" SimAuthAgent.spec --clean --noconfirm
if errorlevel 1 (
    echo [ОШИБКА] PyInstaller завершился с ошибкой
    pause & exit /b 1
)

echo.
echo [2/3] Копирование конфига (шаблон)...
copy /Y "%AGENT%\config.json" "%DIST%\config.json" >nul

echo.
echo [3/3] Готово!
echo.
echo Дистрибутив: %DIST%\
echo   SimAuthAgent.exe  – запустить на игровом ПК
echo   config.json       – настроить под каждый ПК (server_url, pc_id, пути AC)
echo.
echo Скопируй всю папку SimAuthAgent\ на флешку или в сеть.
echo.
pause
