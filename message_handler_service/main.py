import asyncio

from message_handler_service.tools.utils import handle_rabbitmq_messages


async def rabbitmq_handler_main():
    while True:
        try:
            await handle_rabbitmq_messages()
            # Keep the service running
            await asyncio.Future()
        except Exception as e:
            print(f"Error in RabbitMQ handler: {e}")
            await asyncio.sleep(5)  # Retry after 5 seconds

if __name__ == "__main__":
    asyncio.run(rabbitmq_handler_main())
