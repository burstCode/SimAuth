import json
from pathlib import Path
from pydantic import BaseModel

_config_path = Path(__file__).parent / "config.json"


class AcRemoteConfig(BaseModel):
    """Настройки AC-сервера, которые агент патчит в race.ini перед запуском игры."""
    server_ip: str = ""
    server_http_port: int = 0  # HTTP-порт (тот, что показывает CM в браузере серверов)
    password: str | None = None  # None — не патчить, "" — сбросить пароль
    car: str = ""              # REQUESTED_CAR, пусто — не патчить
    skin: str = ""             # CAR_0 SKIN, пусто — не патчить


class AgentConfig(BaseModel):
    server_url: str = "http://localhost:8000"
    pc_id: str = "PC-01"
    ac_exe_path: str = "E:/Games/Steam/steamapps/common/assettocorsa/acs.exe"
    race_ini_path: str = "C:/Users/mikex/OneDrive/Документы/Assetto Corsa/cfg/race.ini"
    race_out_path: str = "C:/Users/mikex/OneDrive/Документы/Assetto Corsa/out/race_out.json"
    steam_exe_path: str = "D:/Games/steam.exe"
    steam_game_id: str = "244210"
    poll_interval_seconds: int = 2
    launch_grace_seconds: int = 30
    ac_remote: AcRemoteConfig = AcRemoteConfig()


def load_config() -> AgentConfig:
    if _config_path.exists():
        data = json.loads(_config_path.read_text(encoding="utf-8"))
        return AgentConfig(**data)
    return AgentConfig()


def save_remote_config(rc: AcRemoteConfig) -> None:
    """Сохраняет ac_remote в config.json и обновляет объект config в памяти."""
    config.ac_remote = rc
    data = json.loads(_config_path.read_text(encoding="utf-8")) if _config_path.exists() else {}
    data["ac_remote"] = rc.model_dump()
    _config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


config = load_config()
