from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Создает основную клавиатуру бота
    
    Args:
        is_admin: Является ли пользователь администратором
        
    Returns:
        ReplyKeyboardMarkup: Основная клавиатура
    """
    kb = ReplyKeyboardBuilder()
    
    # Основные кнопки для всех пользователей
    kb.add(KeyboardButton(text="👤 Профиль"))
    kb.add(KeyboardButton(text="💰 Пополнить"))
    kb.add(KeyboardButton(text="🛒 Купить"))
    kb.add(KeyboardButton(text="📦 Наличие товаров"))
    kb.add(KeyboardButton(text="📞 Поддержка"))
    
    # Кнопки только для администраторов
    if is_admin:
        kb.add(KeyboardButton(text="⚙️ Настройки"))
        kb.add(KeyboardButton(text="📊 Финансы и статистика"))
        kb.add(KeyboardButton(text="🛠 Админ-панель"))
    
    # Настраиваем сетку кнопок (2 в ряд)
    kb.adjust(2)
    
    return kb.as_markup(resize_keyboard=True)