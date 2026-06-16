"""
Точка входа для PyInstaller.
Используем объект `app` напрямую — строковый импорт "main:app" не работает в frozen-режиме.
"""
import multiprocessing
import uvicorn
from config import config
from main import app

if __name__ == "__main__":
    multiprocessing.freeze_support()  # обязательно для Windows + PyInstaller
    print(f"SimAuth Server запускается на {config.host}:{config.port}")
    print("Ctrl+C — остановить\n")
    uvicorn.run(app, host=config.host, port=config.port)
