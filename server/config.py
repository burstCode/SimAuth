import json
import sys
from pathlib import Path
from pydantic import BaseModel


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


_config_path = _base_dir() / "config.json"


class OtpSenderConfig(BaseModel):
    type: str = "log"
    model_config = {"extra": "allow"}


class AcRemoteConfig(BaseModel):
    server_ip: str = ""
    server_http_port: int = 0
    password: str | None = None
    car: str = ""
    skin: str = ""


class ServerConfig(BaseModel):
    session_duration_minutes: int = 10
    otp_ttl_minutes: int = 5
    db_path: str = "simauth.db"
    host: str = "0.0.0.0"
    port: int = 8000
    timezone: str = "Europe/Moscow"
    admin_password: str = "admin"
    otp_sender: OtpSenderConfig = OtpSenderConfig()
    ac_remote: AcRemoteConfig = AcRemoteConfig()


def load_config() -> ServerConfig:
    if _config_path.exists():
        data = json.loads(_config_path.read_text(encoding="utf-8"))
        return ServerConfig(**data)
    return ServerConfig()


def save_config() -> None:
    _config_path.write_text(
        json.dumps(config.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_tournament_config(rc: AcRemoteConfig) -> None:
    config.ac_remote = rc
    save_config()


config = load_config()
