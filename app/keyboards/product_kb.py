from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List

from app.database.models import Product


def get_products_keyboard(products: List[Product]) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру со списком товаров
    
    Args:
        products: Список товаров
        
    Returns:
        InlineKeyboardMarkup: Клавиатура со списком товаров
    """
    kb = InlineKeyboardBuilder()
    
    for product in products:
        kb.add(InlineKeyboardButton(
            text=f"{product.name} - {product.price:.2f}₽",
            callback_data=f"product:{product.id}"
        ))
    
    kb.adjust(1)  # По одной кнопке в ряду
    
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
    
    kb.add(InlineKeyboardButton(
        text="🛒 Купить",
        callback_data=f"buy:{product_id}"
    ))
    
    kb.add(InlineKeyboardButton(
        text="🔙 Назад к списку",
        callback_data="products:list"
    ))
    
    return kb.as_markup()


def get_user_product_actions_keyboard(product_id: str, stars_enabled: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура действий для пользователя (покупка с баланса и, опционально, за звезды)
    """
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(
        text="💳 Купить с баланса",
        callback_data=f"buy:{product_id}"
    ))
    if stars_enabled:
        kb.add(InlineKeyboardButton(
            text="✨ Купить за звезды",
            callback_data=f"buy_stars:{product_id}"
        ))
    kb.add(InlineKeyboardButton(
        text="🔙 Назад к списку",
        callback_data="products:list"
    ))
    return kb.as_markup()


def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру выбора способа оплаты
    
    Returns:
        InlineKeyboardMarkup: Клавиатура выбора способа оплаты
    """
    kb = InlineKeyboardBuilder()
    
    # Отмена
    kb.add(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="pay:cancel"
    ))
    
    return kb.as_markup()


def get_confirm_purchase_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру подтверждения покупки
    
    Returns:
        InlineKeyboardMarkup: Клавиатура подтверждения покупки
    """
    kb = InlineKeyboardBuilder()
    
    kb.add(InlineKeyboardButton(
        text="✅ Проверить оплату",
        callback_data="confirm:payment"
    ))
    
    kb.add(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data="cancel"
    ))
    
    return kb.as_markup()


def get_admin_product_actions_keyboard(product_id: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру действий администратора с товаром
    
    Args:
        product_id: ID товара
        
    Returns:
        InlineKeyboardMarkup: Клавиатура действий администратора
    """
    kb = InlineKeyboardBuilder()
    
    kb.row(
        InlineKeyboardButton(text="📝 Редактировать", callback_data=f"admin:edit_product:{product_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:delete_product:{product_id}")
    )
    
    kb.row(
        InlineKeyboardButton(text="➕ Добавить позиции", callback_data=f"admin:add_items:{product_id}"),
        InlineKeyboardButton(text="📊 Позиции", callback_data=f"admin:view_items:{product_id}")
    )
    
    kb.row(
        InlineKeyboardButton(text="🖼 Изображение", callback_data=f"admin:upload_image:{product_id}"),
        InlineKeyboardButton(text="📖 Инструкция", callback_data=f"admin:set_instruction:{product_id}")
    )
    kb.row(
        InlineKeyboardButton(text="✨ Включить звезды", callback_data=f"admin:stars:on:{product_id}"),
        InlineKeyboardButton(text="🚫 Выключить звезды", callback_data=f"admin:stars:off:{product_id}")
    )
    kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:list_products"))
    
    return kb.as_markup()


def get_items_management_keyboard(product_id: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру управления позициями товара
    
    Args:
        product_id: ID товара
        
    Returns:
        InlineKeyboardMarkup: Клавиатура управления позициями
    """
    kb = InlineKeyboardBuilder()
    
    kb.row(
        InlineKeyboardButton(text="➕ Добавить по одной", callback_data=f"admin:add_item_single:{product_id}"),
        InlineKeyboardButton(text="📦 Добавить пакетом", callback_data=f"admin:add_items_batch:{product_id}")
    )
    
    kb.row(
        InlineKeyboardButton(text="🗑 Удалить позиции", callback_data=f"admin:delete_items:{product_id}")
    )
    
    kb.add(InlineKeyboardButton(
        text="🔙 Назад к товару",
        callback_data=f"admin:product:{product_id}"
    ))
    
    return kb.as_markup()


def get_add_items_method_keyboard(product_id: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру выбора способа добавления позиций
    
    Args:
        product_id: ID товара
        
    Returns:
        InlineKeyboardMarkup: Клавиатура выбора способа
    """
    kb = InlineKeyboardBuilder()
    
    kb.row(
        InlineKeyboardButton(text="📝 По одной", callback_data=f"admin:add_item_single:{product_id}"),
        InlineKeyboardButton(text="📦 Пакетом", callback_data=f"admin:add_items_batch:{product_id}")
    )
    
    kb.add(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data=f"admin:product:{product_id}"
    ))
    
    return kb.as_markup()