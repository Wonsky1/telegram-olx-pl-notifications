"""Business-logic / use-case layer for monitoring.

Depends only on abstract *interfaces* (validator & repository), which
facilitates unit testing and adheres to the Dependency-Inversion
principle.  Telegram-specific concerns live in bot.handlers.* modules.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from repositories.monitoring import MonitoringRepositoryProtocol
from services.validator import UrlValidatorProtocol

logger = logging.getLogger(__name__)

__all__ = [
    "MonitoringSpec",
    "MonitoringService",
]


@dataclass(frozen=True, slots=True)
class MonitoringSpec:
    """Value-object containing validated monitoring parameters."""

    chat_id: str
    name: str
    url: str  # *canonical* URL produced by UrlValidator.normalize()


class MonitoringService:  # noqa: D101 – simple name
    def __init__(
        self,
        repo: MonitoringRepositoryProtocol,
        validator: UrlValidatorProtocol,
    ) -> None:
        self._repo = repo
        self._validator = validator

    # ---------------- Public API used by Telegram handlers ----------------
    def add_monitoring(self, spec: MonitoringSpec) -> None:
        """Validate and persist a new monitoring task.

        Raises ValueError with descriptive message if validation fails so that
        the caller (Telegram handler) can translate it into user-friendly
        messages.
        """
        name = spec.name.strip()
        if not name or len(name) > 64:
            raise ValueError("Name must be between 1 and 64 characters long.")
        if name.startswith("/"):
            raise ValueError("Name may not start with '/'.")

        url = spec.url.strip()
        if not self._validator.is_supported(url):
            raise ValueError("Unsupported URL.")
        url = self._validator.normalize(url)
        if not self._validator.is_reachable(url):
            raise ValueError("URL not reachable.")
        # Check duplicates
        if self._repo.has_url(spec.chat_id, url):
            raise ValueError("Duplicate URL for this chat.")
        if self._repo.task_exists(spec.chat_id, name):
            raise ValueError("Duplicate name for this chat.")
        # Everything OK → persist
        self._repo.create_task(spec.chat_id, name, url)
        logger.info("Monitoring '%s' created for chat_id %s", name, spec.chat_id)

    def remove_monitoring(self, chat_id: str, name: str) -> None:
        """Delete monitoring task.

        Raises ValueError if it does not exist so that UI can respond.
        """
        if not self._repo.task_exists(chat_id, name):
            raise ValueError("Monitoring not found.")
        self._repo.delete_task(chat_id, name)
        logger.info("Monitoring '%s' deleted for chat_id %s", name, chat_id)

    def list_monitorings(self, chat_id: str):  # -> Sequence[MonitoringTask]
        return self._repo.list_tasks(chat_id)

    # ---------------- Background-worker helpers (pass-through) ----------------
    def pending_tasks(self):
        return self._repo.pending_tasks()

    def items_to_send(self, task):
        return self._repo.items_to_send(task)

    def update_last_got_item(self, chat_id: str) -> None:
        self._repo.update_last_got_item(chat_id)

    def update_last_updated(self, task) -> None:
        self._repo.update_last_updated(task)
