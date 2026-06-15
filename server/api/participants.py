from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from eligibility import check_eligible
from models import Participant, IdentityDocument, IdentityType, OtpCode
from schemas import (
    ParticipantRegisterPassport,
    ParticipantRegisterBirthCert,
    ParticipantRegisterPhone,
    ParticipantOut,
    EligibilityCheck,
    EligibilityOut,
)

router = APIRouter(prefix="/participants", tags=["participants"])


def _find_by_hash(identity_type: IdentityType, value_hash: str, db: Session) -> Participant | None:
    doc = (
        db.query(IdentityDocument)
        .filter_by(identity_type=identity_type, value_hash=value_hash)
        .first()
    )
    return doc.participant if doc else None


def _create_participant(full_name: str, identity_type: IdentityType, value_hash: str, db: Session) -> Participant:
    participant = Participant(full_name=full_name)
    db.add(participant)
    db.flush()
    doc = IdentityDocument(
        participant_id=participant.id,
        identity_type=identity_type,
        value_hash=value_hash,
    )
    db.add(doc)
    db.commit()
    db.refresh(participant)
    return participant



def _check_name_match(participant: Participant, submitted_name: str) -> None:
    """Если документ уже есть в БД — ФИО должно совпадать."""
    if participant.full_name != submitted_name:
        raise HTTPException(
            409,
            f"Документ уже зарегистрирован на «{participant.full_name}». "
            "Если это ошибка — обратитесь к администратору.",
        )


@router.post("/passport", response_model=ParticipantOut, status_code=201)
def register_by_passport(body: ParticipantRegisterPassport, db: Session = Depends(get_db)):
    value_hash = IdentityDocument.make_hash(
        IdentityType.PASSPORT, body.passport_series, body.passport_number
    )
    participant = _find_by_hash(IdentityType.PASSPORT, value_hash, db)
    if participant:
        _check_name_match(participant, body.full_name)
        return participant
    return _create_participant(body.full_name, IdentityType.PASSPORT, value_hash, db)


@router.post("/birth-cert", response_model=ParticipantOut, status_code=201)
def register_by_birth_cert(body: ParticipantRegisterBirthCert, db: Session = Depends(get_db)):
    value_hash = IdentityDocument.make_hash(
        IdentityType.BIRTH_CERT, body.cert_series, body.cert_number
    )
    participant = _find_by_hash(IdentityType.BIRTH_CERT, value_hash, db)
    if participant:
        _check_name_match(participant, body.full_name)
        return participant
    return _create_participant(body.full_name, IdentityType.BIRTH_CERT, value_hash, db)


@router.post("/phone", response_model=ParticipantOut, status_code=201)
def register_by_phone(body: ParticipantRegisterPhone, db: Session = Depends(get_db)):
    otp = (
        db.query(OtpCode)
        .filter_by(phone=body.phone, code=body.otp_code, used=False)
        .order_by(OtpCode.created_at.desc())
        .first()
    )
    if not otp or not otp.is_valid:
        raise HTTPException(400, "Неверный или истёкший код подтверждения")

    otp.used = True
    value_hash = IdentityDocument.make_hash(IdentityType.PHONE, body.phone)
    participant = _find_by_hash(IdentityType.PHONE, value_hash, db)
    if participant:
        _check_name_match(participant, body.full_name)
    else:
        participant = _create_participant(body.full_name, IdentityType.PHONE, value_hash, db)

    db.commit()
    return participant


@router.post("/eligibility", response_model=EligibilityOut)
def check_eligibility(body: EligibilityCheck, db: Session = Depends(get_db)):
    value_hash = IdentityDocument.make_hash(body.identity_type, *body.value_parts)
    participant = _find_by_hash(body.identity_type, value_hash, db)
    if not participant:
        return EligibilityOut(eligible=True)
    eligible, reason = check_eligible(participant, db)
    return EligibilityOut(eligible=eligible, reason=reason, participant=participant)
