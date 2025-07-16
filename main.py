# telegram_service.py
import asyncio
import logging
from datetime import datetime, timedelta, timezone
import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from db.database import (
    get_db, 
    get_items_to_send_for_task, 
    init_db, 
    create_task, 
    delete_task_by_chat_id,
    update_last_got_item,
    get_pending_tasks,
    get_task_by_chat_id
)
from tools.texts import get_link, get_valid_url
from core.config import settings

# Warsaw timezone
WARSAW_TZ = pytz.timezone('Europe/Warsaw')

def now_warsaw():
    """Get current datetime in Warsaw timezone as naive datetime"""
    # Get current UTC time, convert to Warsaw timezone, then make it naive
    utc_now = datetime.now(timezone.utc)
    warsaw_now = utc_now.astimezone(WARSAW_TZ)
    return warsaw_now.replace(tzinfo=None)  # Remove timezone info for database storage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        # logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger(__name__)

init_db()


async def check_and_send_items(bot):
    """Check for new items and send them to users"""
    db = next(get_db())
    
    try:
        # Get all users who need item updates using the provided function
        pending_tasks = get_pending_tasks(db)

        for task in pending_tasks:            
            items_to_send = get_items_to_send_for_task(db, task)
            logger.info(f"Found {len(items_to_send)} items to send for chat_id {task.chat_id}")
            if items_to_send:
                await bot.send_photo(
                    chat_id=task.chat_id,
                    photo="https://tse4.mm.bing.net/th?id=OIG2.fso8nlFWoq9hafRkva2e&pid=ImgGn",
                    caption=f"I have found {len(items_to_send)} items, maybe one of them is what you're looking for",
                )
                
                for item in items_to_send[::-1]:
                    desc_lines = item.description.strip().split('\n')
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
                    
                    text = (
                        f"📦 *{item.title}*\n\n"
                        f"💰 *Price:* {item.price}\n"
                        f"📍 *Location:* {item.location}\n"
                        f"🕒 *Posted:* {item.created_at_pretty}\n"
                    )
                    
                    if price_info:
                        text += f"💵 *{price_info}* PLN\n"
                    if deposit_info and deposit_info != "Deposit: 0":
                        text += f"🔐 *{deposit_info}* PLN\n"
                    if animals_info:
                        text += f"🐾 *{animals_info}*\n"
                    if rent_info and rent_info != "Additional rent: 0":
                        text += f"📊 *{rent_info}* PLN\n"
                    
                    text += f"\n🔗 [View listing]({item.item_url})"
                    
                    if item.image_url and item.image_url.startswith("http"):
                        await bot.send_photo(
                            chat_id=task.chat_id, 
                            photo=item.image_url, 
                            caption=text, 
                            parse_mode="Markdown"
                        )
                    else:
                        await bot.send_message(
                            chat_id=task.chat_id, 
                            text=text, 
                            parse_mode="Markdown"
                        )
                    
                    await asyncio.sleep(0.5)  # Adjust the delay as needed
                
                # Update the last_got_item timestamp using the provided function
                update_last_got_item(db, task.chat_id)
                
                # Update last_updated too
                task.last_updated = now_warsaw()
                db.commit()
                logger.info(f"Updated timestamps for chat_id {task.chat_id}")
            else:
                logger.debug(f"No new items for chat_id {task.chat_id}")
                # Don't update timestamps when no new items are found
                # Only update last_updated to indicate the check was performed
                task.last_updated = now_warsaw()
                db.commit()


    except Exception as e:
        logger.error(f"Error in check_and_send_items: {e}", exc_info=True)
    finally:
        db.close()


async def periodic_check(bot):
    """Periodically check for new items and send them to users"""
    while True:
        try:
            logger.debug("Starting periodic check")
            await check_and_send_items(bot)
        except Exception as e:
            logger.error(f"Error in periodic check: {e}", exc_info=True)
        logger.info(f"Sleeping for {settings.CHECK_FREQUENCY_SECONDS} seconds")
        await asyncio.sleep(settings.CHECK_FREQUENCY_SECONDS)  # Check according to settings


async def telegram_main():
    # Initialize bot
    logger.info("Initializing bot")
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    
    # Command handlers
    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        logger.info(f"Start command received from chat_id {message.chat.id}")
        kb = [
            [
                types.KeyboardButton(text="Start monitoring"),
                types.KeyboardButton(text="Stop monitoring"),
            ],
            [
                types.KeyboardButton(text="Status"),
            ],
        ]
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=kb,
            resize_keyboard=True,
            input_field_placeholder="Start, stop monitoring, or check status",
        )
        await message.answer("Hello Yana, this is a bot for you <3", reply_markup=keyboard)
    
    @dp.message(Command(commands=["start_monitoring"]))
    async def start_monitoring(message: types.Message):
        logger.info(f"Start monitoring command received from chat_id {message.chat.id}")
        db = next(get_db())
        try:
            url = get_link(message.text)
            url = get_valid_url(url, settings.URL)
            logger.debug(f"Using URL: {url}")
            task = get_task_by_chat_id(db, str(message.chat.id))
            if not task:
                create_task(db, str(message.chat.id), url)
                logger.info(f"Created monitoring task for chat_id {message.chat.id}")
                await message.answer(f"Monitoring started for url:\n🔗 [View url]({url})\nYou'll receive updates about new items.", parse_mode="Markdown")
            else:
                logger.debug(f"Monitoring already started for chat_id {message.chat.id}")
                await message.answer("Monitoring is already started")
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}", exc_info=True)
            await message.answer("Error starting monitoring. Please try again.")
        finally:
            db.close()
    
    @dp.message(Command(commands=["stop_monitoring"]))
    async def stop_monitoring(message: types.Message):
        logger.info(f"Stop monitoring command received from chat_id {message.chat.id}")
        db = next(get_db())
        try:
            task = get_task_by_chat_id(db, str(message.chat.id))
            if task:
                delete_task_by_chat_id(db, str(message.chat.id))
                logger.info(f"Deleted monitoring task for chat_id {message.chat.id}")
                await message.answer("Monitoring stopped")
            else:
                logger.debug(f"No monitoring task found for chat_id {message.chat.id}")
                await message.answer("Monitoring is already stopped")
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}", exc_info=True)
            await message.answer("Error stopping monitoring. Please try again.")
        finally:
            db.close()
    
    @dp.message(Command(commands=["status"]))
    async def status(message: types.Message):
        logger.info(f"Status command received from chat_id {message.chat.id}")
        db = next(get_db())
        try:
            task = get_task_by_chat_id(db, str(message.chat.id))
            if task:
                status_text = (
                    f"✅ *Monitoring is ACTIVE*\n\n"
                    f"🔗 *URL:* [View link]({task.url})\n"
                    f"🕒 *Last updated:* {task.last_updated.strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                if task.last_got_item:
                    status_text += f"📦 *Last item found:* {task.last_got_item.strftime('%Y-%m-%d %H:%M:%S')}\n"
                else:
                    status_text += f"📦 *Last item found:* Never\n"
                await message.answer(status_text, parse_mode="Markdown")
            else:
                await message.answer("📋 *No active monitoring found*\n\nYou don't have any monitoring tasks set up.\nStart your monitoring to begin monitoring.", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error getting status: {e}", exc_info=True)
            await message.answer("Error getting status. Please try again.")
        finally:
            db.close()
    
    # Text button handlers
    @dp.message(lambda message: message.text == "Start monitoring")
    async def start_monitoring_button(message: types.Message):
        # Call the same logic as the command handler
        await start_monitoring(message)
    
    @dp.message(lambda message: message.text == "Stop monitoring")
    async def stop_monitoring_button(message: types.Message):
        # Call the same logic as the command handler
        await stop_monitoring(message)
    
    @dp.message(lambda message: message.text == "Status")
    async def status_button(message: types.Message):
        # Call the same logic as the command handler
        await status(message)
    
    # Start periodic check for new items
    logger.info("Starting periodic check for new items...")
    asyncio.create_task(periodic_check(bot))
    
    # Start polling
    logger.info("Starting bot polling...")
    chat_id = settings.CHAT_IDS
    try:
        await bot.send_message(chat_id=chat_id, text="BOT WAS STARTED")
        logger.info(f"Bot started notification sent to chat_id {chat_id}")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Fatal error in telegram_main: {e}", exc_info=True)
    finally:
        logger.info("Bot stopped, sending notification")
        await bot.send_message(chat_id=chat_id, text="BOT WAS STOPPED")


if __name__ == "__main__":
    logger.info("Starting telegram service...")
    asyncio.run(telegram_main())
