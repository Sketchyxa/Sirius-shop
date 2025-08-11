from aiogram.fsm.state import StatesGroup, State


class TokenSettings(StatesGroup):
    """Состояния для настройки токенов платежных систем"""
    enter_crypto_pay_token = State()  # Ввод токена Crypto Pay
    confirm_token = State()  # Подтверждение токена


class ProductManagement(StatesGroup):
    """Состояния для управления товарами"""
    add_category = State()  # Добавление категории
    edit_category = State()  # Редактирование категории
    delete_category_confirm = State()  # Подтверждение удаления категории
    
    add_product_name = State()  # Добавление товара - название
    add_product_description = State()  # Добавление товара - описание
    add_product_price = State()  # Добавление товара - цена
    add_product_category = State()  # Добавление товара - категория
    
    edit_product_name = State()  # Редактирование товара - название
    edit_product_description = State()  # Редактирование товара - описание
    edit_product_price = State()  # Редактирование товара - цена
    edit_product_category = State()  # Редактирование товара - категория
    delete_product_confirm = State()  # Подтверждение удаления товара
    upload_image = State()  # Загрузка изображения товара
    edit_product_instruction = State()  # Установка ссылки на инструкцию
    
    add_items = State()  # Добавление позиций товара
    add_items_batch = State()  # Добавление позиций товара пакетом


class UserSearch(StatesGroup):
    """Состояния для поиска пользователей"""
    enter_user_id = State()  # Ввод ID пользователя
    enter_receipt_id = State()  # Ввод номера чека


class Broadcast(StatesGroup):
    """Состояния для рассылки сообщений"""
    enter_message = State()  # Ввод текста рассылки
    confirm_broadcast = State()  # Подтверждение рассылки


class BalanceManagement(StatesGroup):
    """Состояния для управления балансом пользователей"""
    enter_new_balance = State()  # Ввод нового значения баланса
    enter_add_balance = State()  # Ввод суммы для выдачи баланса