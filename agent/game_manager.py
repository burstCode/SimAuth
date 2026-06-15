import json
import mmap
import os
import re
import subprocess
from pathlib import Path

from config import config

# ---------------------------------------------------------------------------
# AC Shared Memory — SPageFileGraphic layout (AC SDK)
# Offset 148 = iBestTime (int32, milliseconds)
#   packetId(4) + status(4) + session(4)
#   + currentTime[15](30) + lastTime[15](30) + bestTime[15](30) + split[15](30)
#   + completedLaps(4) + position(4) + iCurrentTime(4) + iLastTime(4)
#   = 148
# ---------------------------------------------------------------------------
_AC_GRAPHICS_SM = "Local\\acpmf_graphics"
_OFFSET_BEST_LAP = 148
_SM_SIZE = 256


def read_best_lap_live() -> int | None:
    """
    Читает лучший круг локального игрока из разделяемой памяти AC (в реальном времени).
    AC должна быть запущена и находиться в сессии.
    """
    try:
        with mmap.mmap(-1, _SM_SIZE, tagname=_AC_GRAPHICS_SM, access=mmap.ACCESS_READ) as sm:
            sm.seek(_OFFSET_BEST_LAP)
            t = int.from_bytes(sm.read(4), "little", signed=True)
            if 0 < t < 1_800_000:  # от 0 до 30 минут — разумный диапазон
                return t
    except Exception:
        pass
    return None


def _fetch_game_port(ip: str, http_port: int) -> int | None:
    """Запрашивает TCP игровой порт из HTTP API AC-сервера (GET /INFO → поле tport)."""
    import urllib.request
    try:
        url = f"http://{ip}:{http_port}/INFO"
        with urllib.request.urlopen(url, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            # tport — TCP-порт (SERVER_PORT в race.ini); port — UDP-порт
            port = data.get("tport") or data.get("port")
            return int(port) if port else None
    except Exception:
        return None


def _patch_field(text: str, section: str, field: str, value: str) -> str:
    """Заменяет field=value внутри указанной секции [section]."""
    def replacer(m: re.Match) -> str:
        return re.sub(rf"(?m)^({re.escape(field)}\s*=).*", rf"\g<1>{value}", m.group(0))
    return re.sub(rf"(?s)\[{re.escape(section)}\].*?(?=\n\[|\Z)", replacer, text)


def patch_race_ini(player_name: str) -> None:
    path = Path(config.race_ini_path)
    text = path.read_text(encoding="utf-8")

    # Имя игрока
    text = _patch_field(text, "REMOTE", "NAME", player_name)
    text = _patch_field(text, "CAR_0", "DRIVER_NAME", player_name)

    # Активируем онлайн-режим
    text = _patch_field(text, "REMOTE", "ACTIVE", "1")

    # Настройки сервера из конфига (только заполненные)
    rc = config.ac_remote
    if rc.server_ip:
        text = _patch_field(text, "REMOTE", "SERVER_IP", rc.server_ip)
    if rc.server_http_port:
        text = _patch_field(text, "REMOTE", "SERVER_HTTP_PORT", str(rc.server_http_port))
        game_port = _fetch_game_port(rc.server_ip, rc.server_http_port)
        if game_port:
            text = _patch_field(text, "REMOTE", "SERVER_PORT", str(game_port))
    if rc.password is not None:
        text = _patch_field(text, "REMOTE", "PASSWORD", rc.password)
    if rc.car:
        text = _patch_field(text, "REMOTE", "REQUESTED_CAR", rc.car)
    if rc.skin:
        text = _patch_field(text, "CAR_0", "SKIN", rc.skin)

    path.write_text(text, encoding="utf-8")


def launch_game() -> subprocess.Popen:
    env = os.environ.copy()
    env["SteamGameId"] = config.steam_game_id
    env["SteamAppId"] = config.steam_game_id
    return subprocess.Popen(
        [config.ac_exe_path],
        cwd=str(Path(config.ac_exe_path).parent),
        env=env,
    )


def is_game_running(process: subprocess.Popen) -> bool:
    return process.poll() is None


def kill_game(process: subprocess.Popen) -> None:
    if is_game_running(process):
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def read_best_lap_from_file(player_name: str) -> int | None:
    """
    Запасной вариант: читает из race_out.json.
    AC записывает этот файл только при нормальном завершении сессии через меню,
    поэтому при принудительном закрытии данные могут быть неполными.
    """
    path = Path(config.race_out_path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if isinstance(data, list):
            data = next((d for d in data if d), None)
        if not data:
            return None

        for extra in data.get("extras", []):
            if extra.get("name") == "bestlap":
                t = extra.get("time", -1)
                if t > 0:
                    return t

        players: list[dict] = data.get("players", [])
        player_idx = next(
            (i for i, p in enumerate(players) if p.get("name") == player_name),
            None,
        )
        if player_idx is None:
            return None

        best = None
        for session in data.get("sessions", []):
            for lap in session.get("laps", []):
                if lap.get("car") == player_idx:
                    t = lap.get("time", -1)
                    if t > 0 and (best is None or t < best):
                        best = t
        return best
    except Exception:
        return None
