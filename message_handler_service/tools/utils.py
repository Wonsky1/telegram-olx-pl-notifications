# rabbitmq_handler.py
import asyncio
import json
from datetime import datetime
from db.database import get_db, MonitoringTask, create_task, delete_task_by_chat_id
from core.rabbitmq_client import RabbitMQClient

async def handle_rabbitmq_messages():
    db = next(get_db())
    rabbit_client = await RabbitMQClient().connect()
    
    # Declare consumer for command messages
    queue = await rabbit_client.channel.declare_queue(
        f"flats_exchange_pending", 
        durable=True
    )
    
    async def on_message(message):
        async with message.process():
            data = json.loads(message.body.decode())
            message_type = data.get("type")
            
            if message_type == "START_MONITORING":
                chat_id = data.get("chat_id")
                url = data.get("url")
                
                # Create or update monitoring task
                task = db.query(MonitoringTask).filter(
                    MonitoringTask.chat_id == chat_id
                ).first()
                
                if not task:
                    create_task(db, chat_id=chat_id, url=url)
                else:
                    task.url = url
                    task.last_updated = datetime.now()
                    db.commit()
            
            elif message_type == "STOP_MONITORING":
                chat_id = data.get("chat_id")
                delete_task_by_chat_id(db, chat_id)
    
    await queue.consume(on_message)
