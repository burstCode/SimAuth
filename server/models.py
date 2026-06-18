import hashlib
import secrets
from datetime import datetime, date, timedelta
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, DateTime, Date, Enum, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class SessionStatus(str, PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class IdentityType(str, PyEnum):
    PASSPORT = "passport"
    BIRTH_CERT = "birth_cert"
    DRIVER_LICENSE = "driver_license"
    PHONE = "phone"


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_name: Mapped[str] = mapped_column(String(100), default="")
    first_name: Mapped[str] = mapped_column(String(100), default="")
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # full_name остаётся в БД для обратной совместимости, вычисляется при создании
    full_name: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def display_name(self) -> str:
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(p for p in parts if p) or self.full_name

    @property
    def game_name(self) -> str:
        """Имя для race.ini: только Фамилия + Имя."""
        if self.last_name and self.first_name:
            return f"{self.last_name} {self.first_name}"
        return self.full_name

    identity_documents: Mapped[list["IdentityDocument"]] = relationship(back_populates="participant")
    sessions: Mapped[list["GameSession"]] = relationship(back_populates="participant")


class IdentityDocument(Base):
    """Верифицирующий документ участника. Один участник может иметь несколько."""
    __tablename__ = "identity_documents"
    __table_args__ = (
        UniqueConstraint("identity_type", "value_hash", name="uq_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"))
    identity_type: Mapped[IdentityType] = mapped_column(Enum(IdentityType), index=True)
    value_hash: Mapped[str] = mapped_column(String(64))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    participant: Mapped["Participant"] = relationship(back_populates="identity_documents")

    @staticmethod
    def make_hash(identity_type: IdentityType, *parts: str) -> str:
        raw = identity_type.value + "|" + "|".join(p.strip().upper() for p in parts)
        return hashlib.sha256(raw.encode()).hexdigest()


class OtpCode(Base):
    """Одноразовый код подтверждения для верификации телефона."""
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code: Mapped[str] = mapped_column(String(6))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

    @staticmethod
    def generate(phone: str, ttl_minutes: int = 5) -> "OtpCode":
        return OtpCode(
            phone=phone,
            code=str(secrets.randbelow(900000) + 100000),
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
        )

    @property
    def is_valid(self) -> bool:
        return not self.used and datetime.utcnow() < self.expires_at


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"))
    pc_id: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.PENDING)
    play_date: Mapped[date] = mapped_column(Date, default=date.today)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    best_lap_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    participant: Mapped["Participant"] = relationship(back_populates="sessions")
