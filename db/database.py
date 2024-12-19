from datetime import datetime, timedelta
from typing import List, Tuple

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import settings

DATABASE_URL = "sqlite:///monitoring.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class MonitoringTask(Base):
    __tablename__ = "monitoring_tasks"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True)
    url = Column(String, nullable=False)
    last_updated = Column(DateTime, nullable=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_task_by_chat_id(db, chat_id: str):
    """Fetch a monitoring task by chat ID."""
    return db.query(MonitoringTask).filter(MonitoringTask.chat_id == chat_id).first()


def create_task(db, chat_id: str, url: str):
    """Create a new monitoring task and store it in the database."""
    new_task = MonitoringTask(chat_id=chat_id, url=url, last_updated=datetime.now())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


def delete_task_by_chat_id(db, chat_id: str):
    """Delete a monitoring task by chat ID."""
    task = get_task_by_chat_id(db, chat_id)
    if task:
        db.delete(task)
        db.commit()


def get_all_tasks(db):
    """Get all monitoring tasks from the database."""
    return db.query(MonitoringTask).all()


def get_users_pending(db) -> List[Tuple[str, str]]:
    """
    Retrieve chat_ids and their associated urls for tasks where
    the last_updated field is older than the threshold defined in settings.TIME.
    """
    time_threshold = datetime.now() - timedelta(seconds=settings.SLEEP_MINUTES * 60)
    tasks = db.query(MonitoringTask.chat_id, MonitoringTask.url).filter(
        MonitoringTask.last_updated < time_threshold
    ).all()
    return tasks
