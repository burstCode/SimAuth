from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import config
from database import get_db
from models import OtpCode
from otp_sender import build_sender
from schemas import OtpRequest, OtpVerify, OtpOut

router = APIRouter(prefix="/otp", tags=["otp"])

_sender = build_sender(config.otp_sender.model_dump())


@router.post("/request", response_model=OtpOut)
def request_otp(body: OtpRequest, db: Session = Depends(get_db)):
    otp = OtpCode.generate(body.phone, ttl_minutes=config.otp_ttl_minutes)
    db.add(otp)
    db.commit()
    try:
        _sender.send(body.phone, otp.code)
    except Exception as e:
        raise HTTPException(502, f"Ошибка отправки кода: {e}")
    return OtpOut(success=True, message=f"Код отправлен на {body.phone}")


@router.post("/verify", response_model=OtpOut)
def verify_otp(body: OtpVerify, db: Session = Depends(get_db)):
    otp = (
        db.query(OtpCode)
        .filter_by(phone=body.phone, code=body.code, used=False)
        .order_by(OtpCode.created_at.desc())
        .first()
    )
    if not otp or not otp.is_valid:
        raise HTTPException(400, "Неверный или истёкший код")
    return OtpOut(success=True, message="Код верный, можно регистрировать")
