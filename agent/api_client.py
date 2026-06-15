import requests
from typing import Any

from config import config


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"HTTP {status}: {detail}")


def _handle(resp: requests.Response) -> Any:
    if not resp.ok:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise ApiError(resp.status_code, detail)
    return resp.json()


def get_pending_session(pc_id: str) -> dict | None:
    resp = requests.get(
        f"{config.server_url}/api/sessions/pending",
        params={"pc_id": pc_id},
        timeout=5,
    )
    return _handle(resp)


def start_session(session_id: int) -> dict:
    resp = requests.post(
        f"{config.server_url}/api/sessions/{session_id}/start",
        timeout=5,
    )
    return _handle(resp)


def complete_session(session_id: int, best_lap_ms: int | None) -> dict:
    resp = requests.post(
        f"{config.server_url}/api/sessions/{session_id}/complete",
        json={"best_lap_ms": best_lap_ms},
        timeout=5,
    )
    return _handle(resp)


def cancel_session(session_id: int) -> dict:
    resp = requests.post(
        f"{config.server_url}/api/sessions/{session_id}/cancel",
        timeout=5,
    )
    return _handle(resp)


def request_otp(phone: str) -> dict:
    resp = requests.post(
        f"{config.server_url}/api/otp/request",
        json={"phone": phone},
        timeout=5,
    )
    return _handle(resp)


def register_passport(full_name: str, series: str, number: str) -> dict:
    resp = requests.post(
        f"{config.server_url}/api/participants/passport",
        json={"full_name": full_name, "passport_series": series, "passport_number": number},
        timeout=5,
    )
    return _handle(resp)


def register_phone(full_name: str, phone: str, otp_code: str) -> dict:
    resp = requests.post(
        f"{config.server_url}/api/participants/phone",
        json={"full_name": full_name, "phone": phone, "otp_code": otp_code},
        timeout=5,
    )
    return _handle(resp)


def create_session(identity_type: str, value_parts: list[str], pc_id: str) -> dict:
    resp = requests.post(
        f"{config.server_url}/api/sessions",
        json={"identity_type": identity_type, "value_parts": value_parts, "pc_id": pc_id},
        timeout=5,
    )
    return _handle(resp)
