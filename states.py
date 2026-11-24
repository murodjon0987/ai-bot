from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    waiting_for_phone = State()

class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_card_info = State()
    waiting_for_manual_credit = State()
