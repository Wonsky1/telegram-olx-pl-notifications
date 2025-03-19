import json
import os
from logging import getLogger

from core.config import settings

import asyncio
import uuid
from typing import MutableMapping
from aio_pika import Message, connect
from aio_pika.abc import (
    AbstractChannel,
    AbstractConnection,
    AbstractQueue,
)
from aio_pika import exceptions


logger = getLogger(__name__)


class RabbitMQClient:
    EXCHANGES = settings.RABBITMQ_EXCHANGES
    QUEUES = settings.RABBITMQ_QUEUES
    connection: AbstractConnection
    channel: AbstractChannel
    callback_queue: AbstractQueue

    def __init__(self) -> None:
        self.futures: MutableMapping[str, asyncio.Future] = {}

    async def ensure_channel(self) -> None:
        """
        Ensures the channel is open and reconnects if it is closed.
        """
        if self.channel.is_closed:
            logger.warning("Channel is closed. Reconnecting...")
            await self.connect()

    async def connect(self) -> "RabbitMQClient":
        self.connection = await connect(
            host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, retries=5
        )
        self.channel = await self.connection.channel()

        for exchange_name in self.EXCHANGES:
            await self.channel.declare_exchange(
                name=exchange_name,
                type="direct",
            )

            for queue in self.QUEUES:
                queue_name = f"{exchange_name}_{queue}"
                declared_queue = await self.channel.declare_queue(
                    name=queue_name, durable=True
                )
                await declared_queue.bind(
                    exchange=exchange_name,
                    routing_key=queue,
                )

        return self

    async def send_message(self, exchange: str, body: dict) -> str:
        await self.ensure_channel()
        message_id = str(uuid.uuid4())
        callback_queue = await self.channel.declare_queue(message_id, auto_delete=True)
        target_exchange = await self.channel.get_exchange(exchange)

        body["reply_to"] = callback_queue.name
        body = json.dumps(body).encode()

        await target_exchange.publish(
            Message(
                body=body,
                content_type="text/plain",
            ),
            routing_key="pending",
        )

        return message_id

    async def get_message_by_id(self, message_id: str) -> str | dict:
        await self.ensure_channel()
        try:
            queue: AbstractQueue = await self.channel.declare_queue(
                message_id, passive=True
            )

            message = await queue.get(timeout=5)

            if message:
                async with message.process():
                    result = message.body.decode()
                    result = json.loads(result)
                    await queue.delete()
                    return result
        except exceptions.QueueEmpty:
            return "Message was not found"
        except Exception as e:
            logger.error(f"Error while retrieving message: {e}")
            return "Message was already retrieved or wrong message id"

    async def close_connection(self) -> None:
        await self.connection.close()
