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


def _create_participant(
    last_name: str, first_name: str, middle_name: str | None,
    identity_type: IdentityType, value_hash: str, db: Session,
) -> Participant:
    full_name = " ".join(p for p in [last_name, first_name, middle_name] if p)
    participant = Participant(
        last_name=last_name,
        first_name=first_name,
        middle_name=middle_name,
        full_name=full_name,
    )
    db.add(participant)
    db.flush()
    db.add(IdentityDocument(
        participant_id=participant.id,
        identity_type=identity_type,
        value_hash=value_hash,
    ))
    db.commit()
    db.refresh(participant)
    return participant


def _check_name_match(participant: Participant, last_name: str, first_name: str) -> None:
    """Фамилия и имя должны совпадать. Отчество не проверяется."""
    stored_last = participant.last_name or participant.full_name.split()[0] if participant.full_name else ""
    stored_first = participant.first_name or (participant.full_name.split()[1] if len(participant.full_name.split()) > 1 else "")
    if stored_last.upper() != last_name.upper() or stored_first.upper() != first_name.upper():
        raise HTTPException(
            409,
            f"Документ уже зарегистрирован на «{participant.display_name}». "
            "Если это ошибка – обратитесь к администратору.",
        )


def _update_middle_name(participant: Participant, middle_name: str | None, db: Session) -> None:
    if not participant.middle_name and middle_name:
        participant.middle_name = middle_name
        participant.full_name = " ".join(p for p in [participant.last_name, participant.first_name, middle_name] if p)
        db.commit()


@router.post("/passport", response_model=ParticipantOut, status_code=201)
def register_by_passport(body: ParticipantRegisterPassport, db: Session = Depends(get_db)):
    value_hash = IdentityDocument.make_hash(
        IdentityType.PASSPORT, body.passport_series, body.passport_number
    )
    participant = _find_by_hash(IdentityType.PASSPORT, value_hash, db)
    if participant:
        _check_name_match(participant, body.last_name, body.first_name)
        _update_middle_name(participant, body.middle_name, db)
        return participant
    return _create_participant(body.last_name, body.first_name, body.middle_name,
                               IdentityType.PASSPORT, value_hash, db)


@router.post("/birth-cert", response_model=ParticipantOut, status_code=201)
def register_by_birth_cert(body: ParticipantRegisterBirthCert, db: Session = Depends(get_db)):
    value_hash = IdentityDocument.make_hash(
        IdentityType.BIRTH_CERT, body.cert_series, body.cert_number
    )
    participant = _find_by_hash(IdentityType.BIRTH_CERT, value_hash, db)
    if participant:
        _check_name_match(participant, body.last_name, body.first_name)
        _update_middle_name(participant, body.middle_name, db)
        return participant
    return _create_participant(body.last_name, body.first_name, body.middle_name,
                               IdentityType.BIRTH_CERT, value_hash, db)


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
        _check_name_match(participant, body.last_name, body.first_name)
        _update_middle_name(participant, body.middle_name, db)
    else:
        participant = _create_participant(body.last_name, body.first_name, body.middle_name,
                                          IdentityType.PHONE, value_hash, db)
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
