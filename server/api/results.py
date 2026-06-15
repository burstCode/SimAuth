from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import GameSession, Participant, SessionStatus
from schemas import LeaderboardEntry

router = APIRouter(prefix="/results", tags=["results"])


@router.get("", response_model=list[LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db)):
    rows = (
        db.query(GameSession, Participant)
        .join(Participant)
        .filter(
            GameSession.status == SessionStatus.COMPLETED,
            GameSession.best_lap_ms.isnot(None),
        )
        .order_by(GameSession.best_lap_ms)
        .all()
    )
    return [
        LeaderboardEntry(
            rank=i + 1,
            full_name=participant.full_name,
            best_lap_ms=session.best_lap_ms,
            play_date=session.play_date,
        )
        for i, (session, participant) in enumerate(rows)
    ]
