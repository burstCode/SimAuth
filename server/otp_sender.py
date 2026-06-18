"""
Абстракция отправки OTP-кодов. Реализация выбирается из config.json:

  "otp_sender": {
    "type": "log"                        # только логирует (для разработки)
    "type": "telegram",                  # Telegram-бот
    "bot_token": "...",
    "type": "sms_smsc",                  # sms.ru / smsc.ru и подобные
    "api_key": "...",
    "sender": "SimAuth"
  }

Добавление нового провайдера: создать класс, унаследовать OtpSender,
зарегистрировать в _REGISTRY.
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class OtpSender(ABC):
    @abstractmethod
    def send(self, phone: str, code: str) -> None:
        """Отправить код на указанный номер. Бросает исключение при ошибке."""


class LogOtpSender(OtpSender):
    """Заглушка для разработки – выводит код в лог."""

    def send(self, phone: str, code: str) -> None:
        logger.warning("OTP [DEV] → %s: %s", phone, code)
        print(f"[DEV OTP] {phone}: {code}")


class TelegramOtpSender(OtpSender):
    """Отправка через Telegram-бота. Требует bot_token в конфиге."""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token

    def send(self, phone: str, code: str) -> None:
        # TODO: реализовать поиск chat_id по номеру телефона через Telegram API
        # либо использовать заранее известный chat_id для клуба
        raise NotImplementedError("Telegram OTP sender not yet implemented")


class SmsSmscSender(OtpSender):
    """Отправка SMS через SMSC.ru или аналогичный сервис."""

    def __init__(self, api_key: str, sender: str = "SimAuth"):
        self.api_key = api_key
        self.sender = sender

    def send(self, phone: str, code: str) -> None:
        # TODO: реализовать HTTP-запрос к API сервиса
        raise NotImplementedError("SMS sender not yet implemented")


_REGISTRY: dict[str, type[OtpSender]] = {
    "log": LogOtpSender,
    "telegram": TelegramOtpSender,
    "sms_smsc": SmsSmscSender,
}


def build_sender(sender_config: dict) -> OtpSender:
    sender_type = sender_config.get("type", "log")
    cls = _REGISTRY.get(sender_type)
    if cls is None:
        raise ValueError(f"Unknown OTP sender type: {sender_type!r}")
    cfg = {k: v for k, v in sender_config.items() if k != "type"}
    return cls(**cfg)
