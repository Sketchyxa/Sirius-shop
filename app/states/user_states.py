from aiogram.fsm.state import StatesGroup, State


class BuyProduct(StatesGroup):
    """Состояния для покупки товара"""
    select_product = State()  # Выбор товара
    confirm_purchase = State()  # Подтверждение покупки
    select_payment_method = State()  # Выбор способа оплаты
    waiting_payment = State()  # Ожидание оплаты


class SupportRequest(StatesGroup):
    """Состояния для запроса в поддержку"""
    enter_message = State()  # Ввод сообщения
    confirm_send = State()  # Подтверждение отправки


class AddProduct(StatesGroup):
    """Состояния для добавления товара (админ)"""
    enter_name = State()  # Ввод названия
    enter_description = State()  # Ввод описания
    enter_price = State()  # Ввод цены
    enter_quantity = State()  # Ввод количества
    upload_image = State()  # Загрузка изображения
    confirm_add = State()  # Подтверждение добавления