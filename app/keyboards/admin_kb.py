from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_admin_settings_keyboard(maintenance_mode: bool, payments_enabled: bool, purchases_enabled: bool) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек для администраторов
    
    Args:
        maintenance_mode: Режим технических работ
        payments_enabled: Включены ли пополнения
        purchases_enabled: Включены ли покупки
        
    Returns:
        InlineKeyboardMarkup: Клавиатура настроек
    """
    kb = InlineKeyboardBuilder()
    
    # Кнопки переключения режимов с правильной логикой цветов
    # Зеленый = включено, Красный = выключено
    if maintenance_mode:
        kb.add(InlineKeyboardButton(text="🟢 Тех. работы: ВКЛЮЧЕНЫ (нажмите для выключения)", callback_data="admin:toggle_maintenance"))
    else:
        kb.add(InlineKeyboardButton(text="🔴 Тех. работы: ВЫКЛЮЧЕНЫ (нажмите для включения)", callback_data="admin:toggle_maintenance"))
    
    if payments_enabled:
        kb.add(InlineKeyboardButton(text="🟢 Пополнения: ВКЛЮЧЕНЫ (нажмите для выключения)", callback_data="admin:toggle_payments"))
    else:
        kb.add(InlineKeyboardButton(text="🔴 Пополнения: ВЫКЛЮЧЕНЫ (нажмите для включения)", callback_data="admin:toggle_payments"))
    
    if purchases_enabled:
        kb.add(InlineKeyboardButton(text="🟢 Покупки: ВКЛЮЧЕНЫ (нажмите для выключения)", callback_data="admin:toggle_purchases"))
    else:
        kb.add(InlineKeyboardButton(text="🔴 Покупки: ВЫКЛЮЧЕНЫ (нажмите для включения)", callback_data="admin:toggle_purchases"))
    
    # Дополнительные кнопки
    kb.row(
        InlineKeyboardButton(text="📊 Логи", callback_data="admin:logs"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:refresh_settings")
    )
    
    # Кнопка настройки платежных систем
    kb.add(InlineKeyboardButton(text="💰 Настройка платежей", callback_data="admin:payment_settings"))
    
    # Кнопка возврата
    kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back_to_main"))
    
    return kb.as_markup()


def get_payment_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек платежных систем
    
    Returns:
        InlineKeyboardMarkup: Клавиатура настроек платежей
    """
    kb = InlineKeyboardBuilder()
    
    kb.add(InlineKeyboardButton(text="🪙 Настроить Crypto Pay", callback_data="admin:setup_crypto_pay"))
    kb.add(InlineKeyboardButton(text="🔄 Проверить Crypto Pay", callback_data="admin:check_crypto_pay"))
    kb.add(InlineKeyboardButton(text="🗑 Удалить токен Crypto Pay", callback_data="admin:delete_crypto_pay_token"))
    kb.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back_to_settings"))
    
    return kb.as_markup()


def get_products_management_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру управления товарами
    
    Returns:
        InlineKeyboardMarkup: Клавиатура управления товарами
    """
    kb = InlineKeyboardBuilder()
    
    kb.row(
        InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin:add_category")
    )
    kb.row(
        InlineKeyboardButton(text="📋 Список категорий", callback_data="admin:list_categories")
    )
    kb.row(
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin:add_product")
    )
    kb.row(
        InlineKeyboardButton(text="📋 Список товаров", callback_data="admin:list_products")
    )
    kb.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back_to_settings")
    )
    
    return kb.as_markup()


def get_search_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру для поиска пользователя или чека
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура поиска
    """
    kb = ReplyKeyboardBuilder()
    
    kb.row(
        KeyboardButton(text="🔍 Поиск по ID пользователя")
    )
    kb.row(
        KeyboardButton(text="🧾 Поиск по номеру чека")
    )
    kb.row(
        KeyboardButton(text="🔙 Назад")
    )
    
    return kb.as_markup(resize_keyboard=True)


def get_category_actions_keyboard(category_id: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру действий с категорией
    
    Args:
        category_id: ID категории
        
    Returns:
        InlineKeyboardMarkup: Клавиатура действий с категорией
    """
    kb = InlineKeyboardBuilder()
    
    kb.row(
        InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"admin:edit_category:{category_id}")
    )
    kb.row(
        InlineKeyboardButton(text="❌ Удалить категорию", callback_data=f"admin:delete_category:{category_id}")
    )
    kb.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:list_categories")
    )
    
    return kb.as_markup()


def get_product_actions_keyboard(product_id: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру действий с товаром
    
    Args:
        product_id: ID товара
        
    Returns:
        InlineKeyboardMarkup: Клавиатура действий с товаром
    """
    kb = InlineKeyboardBuilder()
    
    kb.row(
        InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"admin:edit_product_name:{product_id}")
    )
    kb.row(
        InlineKeyboardButton(text="✏️ Изменить описание", callback_data=f"admin:edit_product_description:{product_id}")
    )
    kb.row(
        InlineKeyboardButton(text="✏️ Изменить цену", callback_data=f"admin:edit_product_price:{product_id}")
    )
    kb.row(
        InlineKeyboardButton(text="✏️ Изменить категорию", callback_data=f"admin:edit_product_category:{product_id}")
    )
    kb.row(
        InlineKeyboardButton(text="🖼 Загрузить фото", callback_data=f"admin:upload_product_image:{product_id}")
    )
    kb.row(
        InlineKeyboardButton(text="❌ Удалить товар", callback_data=f"admin:delete_product:{product_id}")
    )
    kb.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:list_products")
    )
    
    return kb.as_markup()


def get_broadcast_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для рассылки
    
    Returns:
        InlineKeyboardMarkup: Клавиатура для рассылки
    """
    kb = InlineKeyboardBuilder()
    
    kb.row(
        InlineKeyboardButton(text="✅ Отправить всем", callback_data="admin:broadcast_confirm")
    )
    kb.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin:broadcast_cancel")
    )
    
    return kb.as_markup()