import ctypes
import json
import re
import sys
import winreg
from pathlib import Path
from pydantic import BaseModel


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


_config_path = _base_dir() / "config.json"

AC_STEAM_APP_ID = "244210"


class AcRemoteConfig(BaseModel):
    server_ip: str = ""
    server_http_port: int = 0
    password: str | None = None
    car: str = ""
    skin: str = ""


class AgentConfig(BaseModel):
    server_url: str = "http://localhost:8000"
    pc_id: str = "PC-01"
    ac_exe_path: str = ""
    race_ini_path: str = ""
    race_out_path: str = ""
    steam_exe_path: str = ""
    poll_interval_seconds: int = 2
    launch_grace_seconds: int = 30


def _documents_folder() -> Path:
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)
    p = Path(buf.value)
    return p if p.exists() else Path.home() / "Documents"


def _steam_root() -> Path | None:
    locations = [
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Valve\Steam", "InstallPath"),
    ]
    for hive, subkey, val_name in locations:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                val, _ = winreg.QueryValueEx(key, val_name)
                p = Path(val)
                if p.exists():
                    return p
        except OSError:
            pass
    return None


def _find_ac_exe(steam: Path) -> str:
    candidates: list[Path] = [
        steam / "steamapps" / "common" / "assettocorsa" / "acs.exe"
    ]
    vdf = steam / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        text = vdf.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'"path"\s+"([^"]+)"', text):
            lib = Path(m.group(1).replace("\\\\", "\\"))
            candidates.append(lib / "steamapps" / "common" / "assettocorsa" / "acs.exe")
    for c in candidates:
        if c.exists():
            return c.as_posix()
    return ""


def _detect_defaults() -> dict:
    docs = _documents_folder()
    ac_docs = docs / "Assetto Corsa"
    result: dict = {
        "race_ini_path": (ac_docs / "cfg" / "race.ini").as_posix(),
        "race_out_path": (ac_docs / "out" / "race_out.json").as_posix(),
    }
    steam = _steam_root()
    if steam:
        steam_exe = steam / "steam.exe"
        if steam_exe.exists():
            result["steam_exe_path"] = steam_exe.as_posix()
        ac_exe = _find_ac_exe(steam)
        if ac_exe:
            result["ac_exe_path"] = ac_exe
    return result


def load_config() -> AgentConfig:
    auto = _detect_defaults()
    if _config_path.exists():
        data = json.loads(_config_path.read_text(encoding="utf-8"))
        merged = {**auto, **data}
    else:
        merged = auto
    return AgentConfig(**merged)


config = load_config()
