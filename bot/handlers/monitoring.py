import logging

from aiogram import types
from aiogram.fsm.context import FSMContext
from olx_db import (
    MonitoringTask,
    create_task,
    delete_task_by_chat_id,
    get_db,
    get_task_by_chat_and_name,
    get_tasks_by_chat_id,
)

from bot.fsm import StartMonitoringForm, StatusForm, StopMonitoringForm
from bot.keyboards import (
    BACK_BUTTON,
    MAIN_MENU_KEYBOARD,
    get_monitoring_selection_keyboard,
)
from bot.responses import (
    BACK_TO_MENU,
    CHOOSE_MONITORING,
    DUPLICATE_NAME,
    DUPLICATE_URL,
    ERROR_CREATING,
    ERROR_STOP,
    INVALID_NAME,
    INVALID_URL,
    MAIN_MENU,
    MONITORING_CREATED,
    NO_MONITORINGS,
    RESERVED_NAME,
    SEND_NAME,
    SEND_URL,
    STOPPED,
    UNKNOWN_MONITORING,
    URL_NOT_REACHABLE,
)
from services.validator import UrlValidator

logger = logging.getLogger(__name__)


async def cmd_start_monitoring(message: types.Message, state: FSMContext):
    logger.info(
        f"Start monitoring questionnaire initiated by chat_id {message.chat.id}"
    )
    await state.set_state(StartMonitoringForm.url)
    kb = types.ReplyKeyboardMarkup(keyboard=[[BACK_BUTTON]], resize_keyboard=True)
    await message.answer(SEND_URL, reply_markup=kb)


async def process_url(message: types.Message, state: FSMContext):
    validator = UrlValidator()
    if message.text.strip() == BACK_BUTTON.text:
        await message.answer(BACK_TO_MENU, reply_markup=MAIN_MENU_KEYBOARD)
        await state.clear()
        return
    url = message.text.strip()
    if not validator.is_supported(url):
        await message.answer(INVALID_URL)
        return
    url = validator.normalize(url)
    if not validator.is_supported(url):
        await message.answer(INVALID_URL)
        return
    if not validator.is_reachable(url):
        await message.answer(URL_NOT_REACHABLE)
        return
    db = next(get_db())
    try:
        if MonitoringTask.has_url_for_chat(db, str(message.chat.id), url):
            await message.answer(DUPLICATE_URL)
            return
    finally:
        db.close()
    await state.update_data(url=url)
    await state.set_state(StartMonitoringForm.name)
    kb = types.ReplyKeyboardMarkup(keyboard=[[BACK_BUTTON]], resize_keyboard=True)
    await message.answer(SEND_NAME, reply_markup=kb)


async def process_name(message: types.Message, state: FSMContext):
    validator = UrlValidator()
    if message.text.strip() == BACK_BUTTON.text:
        await message.answer(BACK_TO_MENU, reply_markup=MAIN_MENU_KEYBOARD)
        await state.clear()
        return
    name = message.text.strip()
    if len(name) == 0 or len(name) > 64:
        await message.answer(INVALID_NAME)
        return
    data = await state.get_data()
    url = validator.normalize(data["url"])
    db = next(get_db())
    try:
        existing = get_task_by_chat_and_name(db, str(message.chat.id), name)
        if existing:
            await message.answer(DUPLICATE_NAME)
            return
        if MonitoringTask.has_url_for_chat(db, str(message.chat.id), url):
            await message.answer(DUPLICATE_URL)
            return
        create_task(db, str(message.chat.id), name, url)
        logger.info(f"Monitoring '{name}' created for chat_id {message.chat.id}")
        await message.answer(
            MONITORING_CREATED.format(name=name, url=url),
            parse_mode="Markdown",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error creating monitoring: {e}", exc_info=True)
        await message.answer(ERROR_CREATING)
    finally:
        db.close()
    await state.clear()


# -------------------- STOP MONITORING --------------------


async def stop_monitoring_command(message: types.Message, state: FSMContext):
    """Ask user which monitoring to stop."""
    db = next(get_db())
    try:
        tasks = get_tasks_by_chat_id(db, str(message.chat.id))
        if not tasks:
            await message.answer(
                "📋 *No active monitoring found*\n\nYou don't have any monitoring tasks set up.\nStart your monitoring to begin monitoring.",
                parse_mode="Markdown",
            )
            return
        kb = get_monitoring_selection_keyboard([t.name for t in tasks])
        await message.answer("Choose monitoring to stop:", reply_markup=kb)
        await state.set_state(StopMonitoringForm.choosing)
    finally:
        db.close()


async def process_stop_choice(message: types.Message, state: FSMContext):
    """Handle user's selection and delete monitoring."""
    name = message.text.strip()
    if name == BACK_BUTTON.text:
        # Go back to main menu
        await message.answer("Back to main menu", reply_markup=MAIN_MENU_KEYBOARD)
        await state.clear()
        return
    # Prevent stopping reserved names
    if name.startswith("/"):
        await message.answer(RESERVED_NAME)
        return
    db = next(get_db())
    try:
        delete_task_by_chat_id(db, str(message.chat.id), name)
        logger.info(f"Monitoring '{name}' deleted for chat_id {message.chat.id}")
        await message.answer(
            STOPPED.format(name=name),
            parse_mode="Markdown",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
    except Exception:
        logger.error("Error deleting monitoring", exc_info=True)
        await message.answer(ERROR_STOP)
    finally:
        db.close()
    await state.clear()


# -------------------- STATUS --------------------


async def status_command(message: types.Message, state: FSMContext):
    """Show status or ask user to choose if multiple monitorings."""
    db = next(get_db())
    try:
        tasks = get_tasks_by_chat_id(db, str(message.chat.id))
        if not tasks:
            await message.answer(NO_MONITORINGS, parse_mode="Markdown")
            return
        if len(tasks) == 1:
            await _send_status(message, tasks[0])
        else:
            kb = get_monitoring_selection_keyboard([t.name for t in tasks])
            await message.answer(CHOOSE_MONITORING, reply_markup=kb)
            await state.set_state(StatusForm.choosing)
    finally:
        db.close()


async def process_status_choice(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if name == BACK_BUTTON.text:
        await message.answer("Back to main menu", reply_markup=MAIN_MENU_KEYBOARD)
        await state.clear()
        return
    db = next(get_db())
    try:
        task = get_task_by_chat_and_name(db, str(message.chat.id), name)
        if task:
            await _send_status(message, task)
            await message.answer(MAIN_MENU, reply_markup=MAIN_MENU_KEYBOARD)
        else:
            await message.answer(UNKNOWN_MONITORING)
            return
    finally:
        db.close()
    await state.clear()


async def _send_status(message: types.Message, task):
    status_text = (
        f"✅ *Monitoring is ACTIVE*\n\n"
        f"📛 *Name:* {task.name}\n"
        f"🔗 *URL:* [View link]({task.url})\n"
        f"🕒 *Last updated:* {task.last_updated.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    if task.last_got_item:
        status_text += (
            f"📦 *Last item sent:* {task.last_got_item.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
    else:
        status_text += f"📦 *Last item sent:* Never\n"
    await message.answer(status_text, parse_mode="Markdown")
