from aiogram.fsm.state import State, StatesGroup


class StartMonitoringForm(StatesGroup):
    url = State()
    name = State()


class StopMonitoringForm(StatesGroup):
    choosing = State()


class StatusForm(StatesGroup):
    choosing = State()
