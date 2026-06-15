from datetime import datetime, date
from pydantic import BaseModel, Field

from models import SessionStatus, IdentityType


# --- Participant ---

class ParticipantRegisterPassport(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    passport_series: str = Field(min_length=4, max_length=4)
    passport_number: str = Field(min_length=6, max_length=6)


class ParticipantRegisterBirthCert(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    cert_series: str = Field(min_length=2, max_length=10)
    cert_number: str = Field(min_length=4, max_length=10)


class ParticipantRegisterPhone(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    phone: str = Field(min_length=10, max_length=20)
    otp_code: str = Field(min_length=6, max_length=6)


class ParticipantOut(BaseModel):
    id: int
    full_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EligibilityCheck(BaseModel):
    identity_type: IdentityType
    # Для passport: series + number; для birth_cert: series + number; для phone: phone
    value_parts: list[str] = Field(
        description="Части идентификатора (серия/номер или номер телефона)"
    )


class EligibilityOut(BaseModel):
    eligible: bool
    reason: str | None = None
    participant: ParticipantOut | None = None


# --- OTP ---

class OtpRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20)


class OtpVerify(BaseModel):
    phone: str
    code: str = Field(min_length=6, max_length=6)


class OtpOut(BaseModel):
    success: bool
    message: str


# --- Session ---

class SessionCreate(BaseModel):
    identity_type: IdentityType
    value_parts: list[str]
    pc_id: str
    duration_minutes: int | None = None


class SessionOut(BaseModel):
    id: int
    pc_id: str
    status: SessionStatus
    play_date: date
    duration_minutes: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    best_lap_ms: int | None
    participant: ParticipantOut

    model_config = {"from_attributes": True}


class SessionComplete(BaseModel):
    best_lap_ms: int | None = None


# --- Results ---

class LeaderboardEntry(BaseModel):
    rank: int
    full_name: str
    best_lap_ms: int
    play_date: date
