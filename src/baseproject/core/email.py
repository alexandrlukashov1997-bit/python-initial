import logging
from typing import Protocol

from baseproject.core.config import settings

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    async def send(self, *, to: str, subject: str, text: str) -> None: ...


class ConsoleEmailSender:
    async def send(self, *, to: str, subject: str, text: str) -> None:
        logger.info(
            "Email from=%s to=%s subject=%s\n%s",
            settings.mail_from,
            to,
            subject,
            text,
        )
