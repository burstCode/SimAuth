"""
Централизованная проверка права на участие в сессии.

Две независимые линии защиты от повторной игры в один день:
  1. По participant_id – прямое совпадение документа.
  2. По full_name – перехватывает попытку прийти с другим документом.
     Имя вводит администратор вживую, поэтому совпадение ФИО надёжно
     указывает на одного человека.
"""

from datetime import date

from sqlalchemy.orm import Session

from models import Participant, GameSession, SessionStatus


def played_today_by_id(participant: Participant, db: Session) -> bool:
    return bool(
        db.query(GameSession)
        .filter(
            GameSession.participant_id == participant.id,
            GameSession.play_date == date.today(),
            GameSession.status.in_([SessionStatus.ACTIVE, SessionStatus.COMPLETED]),
        )
        .first()
    )


def played_today_by_name(full_name: str, db: Session) -> bool:
    """Проверяет, играл ли сегодня кто-либо с таким же ФИО (любой документ)."""
    match = (
        db.query(GameSession)
        .join(Participant)
        .filter(
            Participant.full_name == full_name,
            GameSession.play_date == date.today(),
            GameSession.status.in_([SessionStatus.ACTIVE, SessionStatus.COMPLETED]),
        )
        .first()
    )
    return bool(match)


def check_eligible(participant: Participant, db: Session) -> tuple[bool, str | None]:
    """
    Возвращает (eligible, reason).
    Проверка только по документу: один документ – одна сессия в день.
    Однофамильцы с разными документами не блокируются.
    Контроль за злоупотреблением несколькими документами – на стороне администратора.
    """
    if played_today_by_id(participant, db):
        return False, "Участник уже играл сегодня"
    return True, None
