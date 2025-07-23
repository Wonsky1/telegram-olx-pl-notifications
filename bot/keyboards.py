from aiogram import types

MAIN_MENU_KEYBOARD = types.ReplyKeyboardMarkup(
    keyboard=[
        [
            types.KeyboardButton(text="Start monitoring"),
            types.KeyboardButton(text="Stop monitoring"),
        ],
        [types.KeyboardButton(text="Status")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Start, stop monitoring, or check status",
)

BACK_BUTTON = types.KeyboardButton(text="⬅️ Back")


def get_monitoring_selection_keyboard(names: list[str]) -> types.ReplyKeyboardMarkup:
    kb = [[types.KeyboardButton(text=n)] for n in names]
    kb.append([BACK_BUTTON])
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
