from aiogram.fsm.state import State, StatesGroup


class DepositStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_confirmation = State()


class TopUpStates(StatesGroup):
    waiting_for_amount = State()


class WithdrawStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_address = State()


class AdminStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_amount = State()
    waiting_for_transaction_id = State()
    waiting_for_password = State()
    waiting_for_new_password = State()
