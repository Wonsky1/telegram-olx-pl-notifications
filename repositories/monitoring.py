"""Persistence layer for monitoring tasks.

Wraps existing helper functions from ``olx_db`` so that the rest of the codebase
can depend on an abstraction instead of concrete DB helpers.  This makes it
straight-forward to swap out the storage mechanism or migrate the schema in the
future.
"""

from __future__ import annotations

import contextlib
from typing import Iterable, Protocol, Sequence

# The existing DB helper module that the current code already relies on.
# We keep the import here so that type-checkers have a chance to see symbols,
# and unit tests can monkey-patch it if required.
from olx_db import MonitoringTask
from olx_db import create_task as _create_task
from olx_db import delete_task_by_chat_id as _delete_task_by_chat_id
from olx_db import get_db as _get_db
from olx_db import get_items_to_send_for_task as _get_items_to_send_for_task
from olx_db import get_pending_tasks as _get_pending_tasks
from olx_db import get_task_by_chat_and_name as _get_task_by_chat_and_name
from olx_db import get_tasks_by_chat_id as _get_tasks_by_chat_id
from olx_db import update_last_got_item as _update_last_got_item

__all__ = [
    "MonitoringRepositoryProtocol",
    "MonitoringRepository",
]


class MonitoringRepositoryProtocol(Protocol):
    """Abstract interface for monitoring persistence."""

    # --- CRUD & queries used by the bot ---
    def task_exists(self, chat_id: str, name: str) -> bool:  # noqa: D401 – simple name
        """Return True if a task with *name* exists for *chat_id*."""

    def has_url(self, chat_id: str, url: str) -> bool:  # noqa: D401
        """Return True if the *url* is already monitored for *chat_id*."""

    def create_task(
        self, chat_id: str, name: str, url: str
    ) -> MonitoringTask:  # noqa: D401
        """Persist a new monitoring task and return the model instance."""

    def delete_task(self, chat_id: str, name: str) -> None:
        """Delete monitoring task identified by *name* for the given chat."""

    def list_tasks(self, chat_id: str) -> Sequence[MonitoringTask]:  # noqa: D401
        """Return all monitoring tasks for *chat_id*."""

    # --- Used by background worker ---
    def pending_tasks(self) -> Iterable[MonitoringTask]:  # noqa: D401
        """Return tasks that need to be checked for new items."""

    def items_to_send(self, task: MonitoringTask):  # noqa: D401
        """Return new items that should be sent for *task*."""

    def update_last_got_item(self, chat_id: str) -> None:  # noqa: D401
        """Update `last_got_item` timestamp after sending items."""


class MonitoringRepository(MonitoringRepositoryProtocol):
    """SQLAlchemy-backed implementation delegating to existing helpers."""

    def __init__(self):
        # Nothing to initialise now – we rely on the global get_db() factory.
        pass

    # Internal context manager to acquire / release DB sessions conveniently.
    @contextlib.contextmanager
    def _session(self):
        db = next(_get_db())
        try:
            yield db
        finally:
            db.close()

    # ----------------- CRUD wrappers -----------------
    def task_exists(self, chat_id: str, name: str) -> bool:  # noqa: D401
        with self._session() as db:
            return _get_task_by_chat_and_name(db, chat_id, name) is not None

    def has_url(self, chat_id: str, url: str) -> bool:  # noqa: D401
        with self._session() as db:
            return MonitoringTask.has_url_for_chat(db, chat_id, url)

    def create_task(
        self, chat_id: str, name: str, url: str
    ) -> MonitoringTask:  # noqa: D401
        with self._session() as db:
            task = _create_task(db, chat_id, name, url)
            db.commit()
            return task

    def delete_task(self, chat_id: str, name: str) -> None:
        with self._session() as db:
            _delete_task_by_chat_id(db, chat_id, name)
            db.commit()

    def list_tasks(self, chat_id: str):  # noqa: D401
        with self._session() as db:
            return list(_get_tasks_by_chat_id(db, chat_id))

    # ----------------- Background / worker helpers -----------------
    def pending_tasks(self):  # noqa: D401
        with self._session() as db:
            return list(_get_pending_tasks(db))

    def items_to_send(self, task: MonitoringTask):  # noqa: D401
        with self._session() as db:
            return list(_get_items_to_send_for_task(db, task))

    def update_last_got_item(self, chat_id: str) -> None:  # noqa: D401
        with self._session() as db:
            _update_last_got_item(db, chat_id)
            db.commit()
