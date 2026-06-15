import json
from pathlib import Path
from pydantic import BaseModel

_config_path = Path(__file__).parent / "config.json"


class OtpSenderConfig(BaseModel):
    type: str = "log"
    model_config = {"extra": "allow"}


class ServerConfig(BaseModel):
    session_duration_minutes: int = 10
    otp_ttl_minutes: int = 5
    db_path: str = "simauth.db"
    host: str = "0.0.0.0"
    port: int = 8000
    timezone: str = "Europe/Moscow"
    otp_sender: OtpSenderConfig = OtpSenderConfig()


def load_config() -> ServerConfig:
    if _config_path.exists():
        data = json.loads(_config_path.read_text(encoding="utf-8"))
        return ServerConfig(**data)
    return ServerConfig()


config = load_config()
