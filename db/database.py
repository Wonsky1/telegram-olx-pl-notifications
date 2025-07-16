from datetime import datetime, timedelta, timezone
from typing import List, Tuple
import pytz

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import settings

# Warsaw timezone
WARSAW_TZ = pytz.timezone('Europe/Warsaw')

def now_warsaw():
    """Get current datetime in Warsaw timezone as naive datetime"""
    # Get current UTC time, convert to Warsaw timezone, then make it naive
    utc_now = datetime.now(timezone.utc)
    warsaw_now = utc_now.astimezone(WARSAW_TZ)
    return warsaw_now.replace(tzinfo=None)  # Remove timezone info for database storage

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class MonitoringTask(Base):
    __tablename__ = "monitoring_tasks"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True)
    url = Column(String, nullable=False)
    last_updated = Column(DateTime, nullable=False)
    last_got_item = Column(DateTime, nullable=True)


class ItemRecord(Base):
    __tablename__ = "item_records"
    
    id = Column(Integer, primary_key=True, index=True)
    item_url = Column(String, unique=True, index=True)
    source_url = Column(String, nullable=False, index=True)  # URL from which this item was extracted
    title = Column(String)
    price = Column(String)
    location = Column(String)
    created_at = Column(DateTime)
    created_at_pretty = Column(String)
    image_url = Column(String, nullable=True)
    description = Column(String)
    first_seen = Column(DateTime, default=now_warsaw)


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
    new_task = MonitoringTask(chat_id=chat_id, url=url, last_updated=now_warsaw())
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


def get_pending_tasks(db) -> List[MonitoringTask]:
    """
    Retrieve tasks where the last_got_item is either None or older than DEFAULT_SENDING_FREQUENCY_MINUTES.
    """
    time_threshold = now_warsaw() - timedelta(minutes=settings.DEFAULT_SENDING_FREQUENCY_MINUTES)
    tasks = db.query(MonitoringTask).filter(
        (MonitoringTask.last_got_item == None) | 
        (MonitoringTask.last_got_item < time_threshold)
    ).all()
    return tasks


def update_last_got_item(db, chat_id: str):
    """Update the last_got_item timestamp for a given chat ID."""
    task = get_task_by_chat_id(db, chat_id)
    if task:
        task.last_got_item = now_warsaw()
        db.commit()

def get_items_to_send_for_task(db, task: MonitoringTask) -> List[ItemRecord]:
    """
    Get a list of ItemRecords that should be sent for a given MonitoringTask.
    If the task has a 'last_got_item' timestamp, return items seen after that time.
    Otherwise, return items seen in the last DEFAULT_LAST_MINUTES_GETTING minutes.
    Filter items to only include those matching the exact monitoring source URL.
    """
    items_query = db.query(ItemRecord)

    if task.last_got_item:
        items_to_send = items_query.filter(
            ItemRecord.first_seen > task.last_got_item,
            ItemRecord.source_url == task.url
        ).all()
    else:
        time_threshold = now_warsaw() - timedelta(minutes=settings.DEFAULT_LAST_MINUTES_GETTING)
        items_to_send = items_query.filter(
            ItemRecord.first_seen > time_threshold,
            ItemRecord.source_url == task.url
        ).all()

    return items_to_send
