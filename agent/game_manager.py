import json
import mmap
import os
import re
import subprocess
import urllib.request
from pathlib import Path

from config import AC_STEAM_APP_ID, AcRemoteConfig, config

# SPageFileGraphic shared memory layout (AC SDK):
# packetId(4) + status(4) + session(4) + currentTime[15](30) + lastTime[15](30)
# + bestTime[15](30) + split[15](30) + completedLaps(4) + position(4)
# + iCurrentTime(4) + iLastTime(4) = offset 148 → iBestTime (int32 LE, ms)
_AC_GRAPHICS_SM = "Local\\acpmf_graphics"
_OFFSET_BEST_LAP = 148
_SM_SIZE = 256


def read_best_lap_live() -> int | None:
    try:
        with mmap.mmap(-1, _SM_SIZE, tagname=_AC_GRAPHICS_SM, access=mmap.ACCESS_READ) as sm:
            sm.seek(_OFFSET_BEST_LAP)
            t = int.from_bytes(sm.read(4), "little", signed=True)
            if 0 < t < 1_800_000:
                return t
    except Exception:
        pass
    return None


def _fetch_game_port(ip: str, http_port: int) -> int | None:
    try:
        url = f"http://{ip}:{http_port}/INFO"
        with urllib.request.urlopen(url, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            port = data.get("tport") or data.get("port")
            return int(port) if port else None
    except Exception:
        return None


def _patch_field(text: str, section: str, field: str, value: str) -> str:
    def replacer(m: re.Match) -> str:
        return re.sub(rf"(?m)^({re.escape(field)}\s*=).*", rf"\g<1>{value}", m.group(0))
    return re.sub(rf"(?s)\[{re.escape(section)}\].*?(?=\n\[|\Z)", replacer, text)


def patch_race_ini(player_name: str, rc: AcRemoteConfig | None = None) -> None:
    path = Path(config.race_ini_path)
    text = path.read_text(encoding="utf-8")

    text = _patch_field(text, "REMOTE", "NAME", player_name)
    text = _patch_field(text, "CAR_0", "DRIVER_NAME", player_name)
    text = _patch_field(text, "REMOTE", "ACTIVE", "1")

    if rc:
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
    env["SteamGameId"] = AC_STEAM_APP_ID
    env["SteamAppId"] = AC_STEAM_APP_ID
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
