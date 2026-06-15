from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import config
from database import get_db
from eligibility import check_eligible
from models import IdentityDocument, GameSession, SessionStatus
from schemas import SessionCreate, SessionOut, SessionComplete

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _get_or_404(session_id: int, db: Session) -> GameSession:
    session = db.get(GameSession, session_id)
    if not session:
        raise HTTPException(404, "Сессия не найдена")
    return session


@router.post("", response_model=SessionOut, status_code=201)
def create_session(body: SessionCreate, db: Session = Depends(get_db)):
    value_hash = IdentityDocument.make_hash(body.identity_type, *body.value_parts)
    doc = db.query(IdentityDocument).filter_by(
        identity_type=body.identity_type, value_hash=value_hash
    ).first()
    if not doc:
        raise HTTPException(404, "Участник не зарегистрирован")

    participant = doc.participant
    eligible, reason = check_eligible(participant, db)
    if not eligible:
        raise HTTPException(409, reason)

    db.query(GameSession).filter(
        GameSession.pc_id == body.pc_id,
        GameSession.status == SessionStatus.PENDING,
    ).update({"status": SessionStatus.CANCELLED})

    game_session = GameSession(
        participant_id=participant.id,
        pc_id=body.pc_id,
        duration_minutes=body.duration_minutes or config.session_duration_minutes,
    )
    db.add(game_session)
    db.commit()
    db.refresh(game_session)
    return game_session


@router.get("/pending", response_model=SessionOut | None)
def get_pending_session(pc_id: str, db: Session = Depends(get_db)):
    return (
        db.query(GameSession)
        .filter(GameSession.pc_id == pc_id, GameSession.status == SessionStatus.PENDING)
        .order_by(GameSession.created_at.desc())
        .first()
    )


@router.post("/{session_id}/start", response_model=SessionOut)
def start_session(session_id: int, db: Session = Depends(get_db)):
    game_session = _get_or_404(session_id, db)
    if game_session.status != SessionStatus.PENDING:
        raise HTTPException(409, f"Сессия в статусе {game_session.status}, старт невозможен")
    game_session.status = SessionStatus.ACTIVE
    game_session.started_at = datetime.utcnow()
    db.commit()
    db.refresh(game_session)
    return game_session


@router.post("/{session_id}/complete", response_model=SessionOut)
def complete_session(session_id: int, body: SessionComplete, db: Session = Depends(get_db)):
    game_session = _get_or_404(session_id, db)
    if game_session.status != SessionStatus.ACTIVE:
        raise HTTPException(409, f"Сессия в статусе {game_session.status}, завершение невозможно")
    game_session.status = SessionStatus.COMPLETED
    game_session.completed_at = datetime.utcnow()
    game_session.best_lap_ms = body.best_lap_ms
    db.commit()
    db.refresh(game_session)
    return game_session


@router.post("/{session_id}/cancel", response_model=SessionOut)
def cancel_session(session_id: int, db: Session = Depends(get_db)):
    game_session = _get_or_404(session_id, db)
    if game_session.status not in (SessionStatus.PENDING, SessionStatus.ACTIVE):
        raise HTTPException(409, "Отменить можно только pending или active сессию")
    game_session.status = SessionStatus.CANCELLED
    db.commit()
    db.refresh(game_session)
    return game_session
