from aiogram.fsm.state import State, StatesGroup

class ActionStates(StatesGroup):
    """
    Определяет, какое действие ждет бот.
    """
    awaiting_link_for_download = State() 
    awaiting_link_for_lyrics = State()   
    awaiting_link_for_cover = State()    