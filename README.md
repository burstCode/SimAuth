# SimAuth

> Система регистрации и управления сессиями для симрейсинг-клуба на базе Assetto Corsa

[![Release](https://img.shields.io/github/v/release/burstCode/SimAuth?style=flat-square&color=e51a20)](https://github.com/burstCode/SimAuth/releases/latest)
[![Build](https://img.shields.io/github/actions/workflow/status/burstCode/SimAuth/release.yml?style=flat-square)](https://github.com/burstCode/SimAuth/actions)
[![Python](https://img.shields.io/badge/python-3.13-blue?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

---

## Что это

SimAuth автоматизирует проведение турниров в симрейсинг-клубе:

- участник регистрируется по паспорту
- имя автоматически прописывается в настройки Assetto Corsa – результат в лидерборде будет подписан правильно
- агент на игровом ПК отсчитывает сессию, фиксирует лучшее время круга и блокирует повторный заезд в тот же день
- сервер хранит всю историю и реализует REST API

---

## Архитектура

```
┌─────────────────────────────┐
│   Игровой ПК (SimAuthAgent) │
│  PyQt6 · полноэкранный UI   │
│  · регистрация участника    │
│  · патч race.ini → acs.exe  │
│  · таймер сессии            │
│  · захват времени круга     │
└────────────┬────────────────┘
             │ HTTP / LAN
┌────────────▼─────────────────┐
│  Админский ПК (SimAuthServer)│
│  PyQt6 · системный трей      │
│  FastAPI · SQLite            │
│  · журнал запросов           │
│  · конфигурация              │
│  · база данных (admin mode)  │
└──────────────────────────────┘
```

---

## Компоненты

### SimAuthAgent – агент на игровом ПК

Полноэкранное PyQt6-приложение, которое стоит на каждом игровом ПК.

**Возможности:**
- Ввод фамилии, имени и отчества + серии/номера паспорта
- Верификация документа (вычисляется SHA-256 хэш, в непосредственном виде документ в базе не хранится)
- Проверка повторного заезда в тот же день
- Автоматический патч `race.ini` ─ имя участника появляется в AC без ручного ввода
- Запуск `acs.exe` напрямую, минуя Content Manager
- Обратный отсчёт сессии с живым отображением лучшего времени круга
- Индикатор подключения к серверу

### SimAuthServer – серверное приложение

Десктопное PyQt6-приложение для административного ПК. Работает в системном трее.

**Возможности:**
- Встроенный FastAPI-сервер, который запускается в фоновом потоке
- **Журнал** – цветной вывод логов uvicorn в реальном времени
- **Конфигурация** – хост/порт, длительность сессии, пароль AC-сервера, автозапуск при старте Windows
- **База данных** – просмотр участников и сессий; режим суперадминистратора открывает inline-редактирование и удаление записей
- Предупреждение при попытке закрыть приложение во время активных игровых сессий
- Отображение фактической длительности каждой сессии

---

## Скачать

Готовые сборки для Windows доступны на странице [Releases](https://github.com/burstCode/SimAuth/releases/latest):

| Архив | Назначение |
|---|---|
| `SimAuthAgent-vX.X.X.zip` | Агент – распаковать на каждый игровой ПК |
| `SimAuthServer-vX.X.X.zip` | Сервер – распаковать на административный ПК |

В каждом архиве рядом с `.exe` лежит `config.json`. В случае с агентом его нужно настроить, указав ip-адрес и порт сервера.

---

## Конфигурация

### `agent/config.json`

```json
{
  "server_url": "http://192.168.1.100:8000",
  "pc_id": "PC-01",
  "ac_exe_path": "E:/Games/Steam/steamapps/common/assettocorsa/acs.exe",
  "race_ini_path": "C:/Users/User/Documents/Assetto Corsa/cfg/race.ini",
  "poll_interval_seconds": 2
}
```

### `server/config.json`

```json
{
  "host": "0.0.0.0",
  "port": 8000,
  "session_duration_minutes": 10,
  "timezone": "Europe/Moscow",
  "admin_password": "admin",
  "db_path": "simauth.db"
}
```

> `admin_password` защищает режим суперадминистратора в SimAuthServer. Поменяйте перед первым запуском.

---

## Сборка из исходников

Требования: Python 3.13, pip.

```bash
# Агент
cd agent
pip install -r requirements.txt pyinstaller
pyinstaller SimAuthAgent.spec --clean --noconfirm

# Сервер
cd server
pip install -r server/requirements.txt pyinstaller
pyinstaller SimAuthServerGUI.spec --clean --noconfirm
```

---

## Стек

| | |
|---|---|
| **UI** | PyQt6 |
| **Backend** | FastAPI + Uvicorn |
| **БД** | SQLite + SQLAlchemy |
| **Валидация** | Pydantic v2 |
| **Сборка** | PyInstaller (`--onedir`) |
| **CI/CD** | GitHub Actions |

---

## Лицензия

MIT
