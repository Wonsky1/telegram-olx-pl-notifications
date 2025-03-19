# telegram_service.py
import asyncio
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from core.config import settings
from core.rabbitmq_client import RabbitMQClient
from tools.utils import get_link

async def listen_for_flats(bot, rabbit_client):
    queue = await rabbit_client.channel.declare_queue(
        f"flats_pending", 
        durable=True
    )
    
    async def on_message(message):
        async with message.process():
            data = json.loads(message.body.decode())
            
            if data.get("type") == "SEND_FLATS":
                chat_id = data.get("chat_id")
                flats = data.get("flats", [])
                
                if flats:
                    # Send the flats to the user
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo="https://tse4.mm.bing.net/th?id=OIG2.fso8nlFWoq9hafRkva2e&pid=ImgGn",
                        caption=f"I have found {len(flats)} flats, maybe one of them is going to be mouse's new flat",
                    )
                    
                    for flat in flats[::-1]:
                        # Parse the description to extract structured information
                        desc_lines = flat.get("description", "").strip().split('\n')
                        price_info = ""
                        deposit_info = ""
                        animals_info = ""
                        rent_info = ""
                        
                        for line in desc_lines:
                            if line.startswith("price:"):
                                price_info = line.replace("price:", "Price:").strip()
                            elif line.startswith("deposit:"):
                                deposit_info = line.replace("deposit:", "Deposit:").strip()
                            elif line.startswith("animals_allowed:"):
                                animals_allowed = line.replace("animals_allowed:", "").strip()
                                if animals_allowed == "true":
                                    animals_info = "Pets: Allowed"
                                elif animals_allowed == "false":
                                    animals_info = "Pets: Not allowed"
                                else:
                                    animals_info = "Pets: Not specified"
                            elif line.startswith("rent:"):
                                rent_info = line.replace("rent:", "Additional rent:").strip()
                        
                        # Format the message with emojis and better structure
                        text = (
                            f"🏠 *{flat.get('title')}*\n\n"
                            f"💰 *Price:* {flat.get('price')}\n"
                            f"📍 *Location:* {flat.get('location')}\n"
                            f"🕒 *Posted:* {flat.get('created_at')}\n"
                        )
                        
                        # Add parsed description details
                        if price_info:
                            text += f"💵 *{price_info}* PLN\n"
                        if deposit_info and deposit_info != "Deposit: 0":
                            text += f"🔐 *{deposit_info}* PLN\n"
                        if animals_info:
                            text += f"🐾 *{animals_info}*\n"
                        if rent_info and rent_info != "Additional rent: 0":
                            text += f"📊 *{rent_info}* PLN\n"
                        
                        # Add link to the listing
                        text += f"\n🔗 [View listing]({flat.get('flat_url')})"
                        
                        # Send the message
                        image_url = flat.get("image_url")
                        if image_url and image_url.startswith("http"):
                            await bot.send_photo(
                                chat_id=chat_id, 
                                photo=image_url, 
                                caption=text, 
                                parse_mode="Markdown"
                            )
                        else:
                            await bot.send_message(
                                chat_id=chat_id, 
                                text=text, 
                                parse_mode="Markdown"
                            )
    
    await queue.consume(on_message)

async def telegram_main():
    # Initialize bot
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    
    # Initialize RabbitMQ client
    rabbit_client = await RabbitMQClient().connect()
    
    # Command handlers
    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        kb = [
            [
                types.KeyboardButton(text="/start_monitoring"),
                types.KeyboardButton(text="/stop_monitoring"),
            ],
        ]
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=kb,
            resize_keyboard=True,
            input_field_placeholder="Start or stop monitoring",
        )
        await message.answer("Hello Yana, this is a bot for you <3", reply_markup=keyboard)
    
    @dp.message(Command(commands=["start_monitoring"]))
    async def start_monitoring(message: types.Message):
        # Send message to RabbitMQ to start monitoring
        await rabbit_client.send_message(
            exchange="flats",
            body={
                "type": "START_MONITORING",
                "chat_id": str(message.chat.id),
                "url": get_link(message.text) or settings.URL
            }
        )
        await message.answer("Starting monitoring... Please wait.")
    
    @dp.message(Command(commands=["stop_monitoring"]))
    async def stop_monitoring(message: types.Message):
        # Send message to RabbitMQ to stop monitoring
        await rabbit_client.send_message(
            exchange="flats",
            body={
                "type": "STOP_MONITORING",
                "chat_id": str(message.chat.id)
            }
        )
        await message.answer("Monitoring stopped.")
    
    # Start listening for flats messages
    asyncio.create_task(listen_for_flats(bot, rabbit_client))
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(telegram_main())
