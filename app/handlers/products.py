from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ParseMode
from loguru import logger
from bson import ObjectId

from app.filters.admin import AdminFilter
from app.states.admin_states import ProductManagement
from app.keyboards import (
    get_products_management_keyboard,
    get_category_actions_keyboard,
    get_admin_product_actions_keyboard,
    get_add_items_method_keyboard,
    get_items_management_keyboard
)
from app.database.repositories import CategoryRepository, ProductRepository, ProductItemRepository


router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.callback_query(F.data == "admin:products_management")
async def products_management(callback: CallbackQuery):
    """Управление товарами"""
    await callback.message.edit_text(
        "📦 <b>Управление товарами</b>\n\n"
        "Выберите действие:",
        reply_markup=get_products_management_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


# Управление категориями

@router.callback_query(F.data == "admin:add_category")
async def add_category(callback: CallbackQuery, state: FSMContext):
    """Добавление новой категории"""
    await state.set_state(ProductManagement.add_category)
    
    await callback.message.edit_text(
        "📂 <b>Добавление категории</b>\n\n"
        "Введите название новой категории товаров.\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.message(ProductManagement.add_category)
async def process_add_category(message: Message, state: FSMContext, category_repo: CategoryRepository):
    """Обработка добавления категории"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Добавление категории отменено",
            reply_markup=get_products_management_keyboard()
        )
        return
    
    category_name = message.text.strip()
    
    if not category_name:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Название категории не может быть пустым.\n"
            "Попробуйте еще раз или нажмите /cancel для отмены.",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        # Создаем новую категорию
        category = await category_repo.create_category(name=category_name)
        
        # Создаем клавиатуру с кнопкой "Назад"
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(
            text="🔙 Назад к управлению товарами",
            callback_data="admin:products_management"
        ))
        
        await message.answer(
            "✅ <b>Категория добавлена</b>\n\n"
            f"Название: <b>{category.name}</b>\n"
            f"ID: <code>{category.id}</code>\n\n"
            "Теперь вы можете добавить товары в эту категорию!",
            reply_markup=kb.as_markup(),
            parse_mode=ParseMode.HTML
        )
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении категории: {e}")
        await message.answer(
            "❌ <b>Ошибка при добавлении категории</b>\n\n"
            "Попробуйте еще раз позже или обратитесь к разработчику.",
            parse_mode=ParseMode.HTML
        )
        await state.clear()


@router.callback_query(F.data == "admin:list_categories")
async def list_categories(callback: CallbackQuery, category_repo: CategoryRepository):
    """Список категорий"""
    categories = await category_repo.get_all_categories()
    
    if not categories:
        await callback.message.edit_text(
            "📂 <b>Список категорий</b>\n\n"
            "Категории не найдены. Добавьте новую категорию.",
            reply_markup=get_products_management_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    
    text = "📂 <b>Список категорий</b>\n\n"
    
    # Создаем клавиатуру с категориями
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    kb = InlineKeyboardBuilder()
    
    for category in categories:
        # Добавляем категорию в текст
        text += f"• <b>{category.name}</b> (ID: <code>{category.id}</code>)\n"
        
        # Добавляем кнопку для управления категорией
        kb.row(InlineKeyboardButton(
            text=f"📂 {category.name}",
            callback_data=f"admin:category:{category.id}"
        ))
    
    # Добавляем кнопку "Назад"
    kb.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="admin:products_management"
    ))
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin:category:"))
async def category_actions(callback: CallbackQuery, category_repo: CategoryRepository):
    """Действия с категорией"""
    # Получаем ID категории
    category_id = callback.data.split(":")[-1]
    
    try:
        # Получаем категорию
        category = await category_repo.get_category(category_id)
        
        if not category:
            await callback.message.edit_text(
                "❌ <b>Ошибка</b>\n\n"
                "Категория не найдена.",
                reply_markup=get_products_management_keyboard(),
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            return
        
        await callback.message.edit_text(
            f"📂 <b>Категория: {category.name}</b>\n\n"
            f"ID: <code>{category.id}</code>\n"
            f"Создана: {category.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            "Выберите действие:",
            reply_markup=get_category_actions_keyboard(str(category.id)),
            parse_mode=ParseMode.HTML
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении категории: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            "Не удалось получить информацию о категории.",
            reply_markup=get_products_management_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin:edit_category:"))
async def edit_category(callback: CallbackQuery, state: FSMContext, category_repo: CategoryRepository):
    """Редактирование категории"""
    # Получаем ID категории
    category_id = callback.data.split(":")[-1]
    
    # Сохраняем ID категории в состоянии
    await state.update_data(category_id=category_id)
    await state.set_state(ProductManagement.edit_category)
    
    # Получаем категорию
    category = await category_repo.get_category(category_id)
    
    await callback.message.edit_text(
        f"📝 <b>Редактирование категории</b>\n\n"
        f"Текущее название: <b>{category.name}</b>\n\n"
        "Введите новое название категории или нажмите /cancel для отмены.",
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.message(ProductManagement.edit_category)
async def process_edit_category(message: Message, state: FSMContext, category_repo: CategoryRepository):
    """Обработка редактирования категории"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Редактирование категории отменено",
            reply_markup=get_products_management_keyboard()
        )
        return
    
    # Получаем ID категории из состояния
    data = await state.get_data()
    category_id = data.get("category_id")
    
    if not category_id:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Не найден ID категории. Попробуйте еще раз.",
            parse_mode=ParseMode.HTML
        )
        await state.clear()
        return
    
    category_name = message.text.strip()
    
    if not category_name:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Название категории не может быть пустым.\n"
            "Попробуйте еще раз или нажмите /cancel для отмены.",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        # Получаем категорию
        category = await category_repo.get_category(category_id)
        
        if not category:
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Категория не найдена.",
                parse_mode=ParseMode.HTML
            )
            await state.clear()
            return
        
        # Обновляем название категории
        old_name = category.name
        category.name = category_name
        await category_repo.update_category(category)
        
        await message.answer(
            "✅ <b>Категория обновлена</b>\n\n"
            f"Старое название: <b>{old_name}</b>\n"
            f"Новое название: <b>{category.name}</b>",
            parse_mode=ParseMode.HTML
        )
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при редактировании категории: {e}")
        await message.answer(
            "❌ <b>Ошибка при редактировании категории</b>\n\n"
            "Попробуйте еще раз позже или обратитесь к разработчику.",
            parse_mode=ParseMode.HTML
        )
        await state.clear()


@router.callback_query(F.data.startswith("admin:delete_category:"))
async def delete_category_confirm(callback: CallbackQuery, state: FSMContext, category_repo: CategoryRepository):
    """Подтверждение удаления категории"""
    # Получаем ID категории
    category_id = callback.data.split(":")[-1]
    
    # Сохраняем ID категории в состоянии
    await state.update_data(category_id=category_id)
    await state.set_state(ProductManagement.delete_category_confirm)
    
    # Получаем категорию
    category = await category_repo.get_category(category_id)
    
    # Создаем клавиатуру для подтверждения
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin:delete_category_confirm:{category_id}"),
        InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"admin:category:{category_id}")
    )
    
    await callback.message.edit_text(
        f"❓ <b>Подтверждение удаления</b>\n\n"
        f"Вы действительно хотите удалить категорию <b>{category.name}</b>?\n\n"
        "⚠️ Внимание! Это действие нельзя отменить!",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete_category_confirm:"))
async def delete_category_process(callback: CallbackQuery, state: FSMContext, category_repo: CategoryRepository):
    """Процесс удаления категории"""
    # Получаем ID категории
    category_id = callback.data.split(":")[-1]
    
    try:
        # Получаем категорию
        category = await category_repo.get_category(category_id)
        
        if not category:
            await callback.message.edit_text(
                "❌ <b>Ошибка</b>\n\n"
                "Категория не найдена.",
                reply_markup=get_products_management_keyboard()
            )
            await callback.answer()
            await state.clear()
            return
        
        # Удаляем категорию
        category_name = category.name
        result = await category_repo.delete_category(category_id)
        
        if result:
            await callback.message.edit_text(
                "✅ <b>Категория удалена</b>\n\n"
                f"Категория <b>{category_name}</b> успешно удалена.",
                reply_markup=get_products_management_keyboard(),
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.edit_text(
                "❌ <b>Ошибка</b>\n\n"
                "Не удалось удалить категорию.",
                reply_markup=get_products_management_keyboard(),
                parse_mode=ParseMode.HTML
            )
        
        await callback.answer()
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при удалении категории: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка при удалении категории</b>\n\n"
            "Попробуйте еще раз позже или обратитесь к разработчику.",
            reply_markup=get_products_management_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        await state.clear()


# Управление товарами

@router.callback_query(F.data == "admin:add_product")
async def add_product(callback: CallbackQuery, state: FSMContext, category_repo: CategoryRepository):
    """Добавление нового товара"""
    # Получаем список категорий
    categories = await category_repo.get_all_categories()
    
    if not categories:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            "Для добавления товара необходимо создать хотя бы одну категорию.",
            reply_markup=get_products_management_keyboard()
        )
        await callback.answer()
        return
    
    # Переходим к вводу названия товара
    await state.set_state(ProductManagement.add_product_name)
    
    await callback.message.edit_text(
        "📦 <b>Добавление товара</b>\n\n"
        "Введите название нового товара.\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.message(ProductManagement.add_product_name)
async def process_add_product_name(message: Message, state: FSMContext):
    """Обработка ввода названия товара"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Добавление товара отменено",
            reply_markup=get_products_management_keyboard()
        )
        return
    
    product_name = message.text.strip()
    
    if not product_name:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Название товара не может быть пустым.\n"
            "Попробуйте еще раз или нажмите /cancel для отмены.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Сохраняем название товара
    await state.update_data(product_name=product_name)
    
    # Переходим к вводу описания
    await state.set_state(ProductManagement.add_product_description)
    
    await message.answer(
        "📝 <b>Добавление товара: описание</b>\n\n"
        "Введите описание товара.\n"
        "Можно использовать HTML-разметку.\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )


@router.message(ProductManagement.add_product_description)
async def process_add_product_description(message: Message, state: FSMContext):
    """Обработка ввода описания товара"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Добавление товара отменено",
            reply_markup=get_products_management_keyboard()
        )
        return
    
    product_description = message.text.strip()
    
    # Сохраняем описание товара
    await state.update_data(product_description=product_description)
    
    # Переходим к вводу цены
    await state.set_state(ProductManagement.add_product_price)
    
    await message.answer(
        "💰 <b>Добавление товара: цена</b>\n\n"
        "Введите цену товара в рублях.\n"
        "Например: <code>100</code> или <code>99.99</code>\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )


@router.message(ProductManagement.add_product_price)
async def process_add_product_price(message: Message, state: FSMContext, category_repo: CategoryRepository):
    """Обработка ввода цены товара"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Добавление товара отменено",
            reply_markup=get_products_management_keyboard()
        )
        return
    
    try:
        product_price = float(message.text.strip().replace(",", "."))
        
        if product_price <= 0:
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Цена товара должна быть положительным числом.\n"
                "Попробуйте еще раз или нажмите /cancel для отмены.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Сохраняем цену товара
        await state.update_data(product_price=product_price)
        
        # Получаем список категорий для выбора
        categories = await category_repo.get_all_categories()
        
        # Создаем клавиатуру для выбора категории
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        
        kb = InlineKeyboardBuilder()
        
        for category in categories:
            kb.row(InlineKeyboardButton(
                text=category.name,
                callback_data=f"admin:add_product_category:{category.id}"
            ))
        
        # Переходим к выбору категории
        await state.set_state(ProductManagement.add_product_category)
        
        await message.answer(
            "📂 <b>Добавление товара: категория</b>\n\n"
            "Выберите категорию для товара:",
            reply_markup=kb.as_markup(),
            parse_mode=ParseMode.HTML
        )
        
    except ValueError:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Цена должна быть числом.\n"
            "Попробуйте еще раз или нажмите /cancel для отмены.",
            parse_mode=ParseMode.HTML
        )


@router.callback_query(ProductManagement.add_product_category, F.data.startswith("admin:add_product_category:"))
async def process_add_product_category(callback: CallbackQuery, state: FSMContext, category_repo: CategoryRepository, product_repo: ProductRepository):
    """Обработка выбора категории товара"""
    # Получаем ID категории
    category_id = callback.data.split(":")[-1]
    
    try:
        # Получаем категорию
        category = await category_repo.get_category(category_id)
        
        if not category:
            await callback.message.edit_text(
                "❌ <b>Ошибка</b>\n\n"
                "Категория не найдена.",
                reply_markup=get_products_management_keyboard()
            )
            await callback.answer()
            await state.clear()
            return
        
        # Сохраняем ID категории
        await state.update_data(category_id=str(category.id))
        
        # Получаем данные о товаре
        data = await state.get_data()
        product_name = data.get("product_name")
        product_description = data.get("product_description")
        product_price = data.get("product_price")
        
        # Создаем товар
        product = await product_repo.create_product(
            name=product_name,
            description=product_description,
            price=product_price,
            category_id=category.id
        )
        
        await callback.message.edit_text(
            "✅ <b>Товар добавлен</b>\n\n"
            f"Название: <b>{product.name}</b>\n"
            f"Описание: {product.description or 'Отсутствует'}\n"
            f"Цена: <b>{product.price:.2f}₽</b>\n"
            f"Категория: <b>{category.name}</b>\n"
            f"ID: <code>{product.id}</code>\n\n"
            "Теперь вы можете добавить количество товара, загрузить изображение или указать ссылку на инструкцию.\n\n"
            "Хотите включить оплату Звездами Telegram для этого товара?",
            reply_markup=get_admin_product_actions_keyboard(str(product.id)),
            parse_mode=ParseMode.HTML
        )
        
        await callback.answer("Товар успешно добавлен")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении товара: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка при добавлении товара</b>\n\n"
            "Попробуйте еще раз позже или обратитесь к разработчику.",
            reply_markup=get_products_management_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        await state.clear()


@router.callback_query(F.data == "admin:list_products")
async def list_products(callback: CallbackQuery, product_repo: ProductRepository, category_repo: CategoryRepository):
    """Список товаров"""
    products = await product_repo.get_all_products()
    
    if not products:
        try:
            await callback.message.edit_text(
                "📦 <b>Список товаров</b>\n\n"
                "Товары не найдены. Добавьте новый товар.",
                reply_markup=get_products_management_keyboard(),
                parse_mode=ParseMode.HTML
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                # Сообщение уже содержит нужный текст, просто отвечаем
                await callback.answer("Список товаров обновлен")
            else:
                # Другая ошибка, пробрасываем её
                raise
        await callback.answer()
        return
    
    text = "📦 <b>Список товаров</b>\n\n"
    
    # Создаем клавиатуру с товарами
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    kb = InlineKeyboardBuilder()
    
    # Получаем категории для отображения названий
    categories = {str(c.id): c.name for c in await category_repo.get_all_categories()}
    
    for product in products:
        category_name = categories.get(str(product.category_id), "Без категории")
        
        # Добавляем товар в текст
        text += (
            f"• <b>{product.name}</b>\n"
            f"  Цена: <b>{product.price:.2f}₽</b>\n"
            f"  Категория: {category_name}\n"
            f"  Количество: {product.quantity} шт.\n"
            f"  ID: <code>{product.id}</code>\n\n"
        )
        
        # Добавляем кнопку для управления товаром
        kb.row(InlineKeyboardButton(
            text=f"📦 {product.name} - {product.price:.2f}₽",
            callback_data=f"admin:product:{product.id}"
        ))
    
    # Добавляем кнопку "Назад"
    kb.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="admin:products_management"
    ))
    
    # Если текст слишком длинный, отправляем только кнопки
    if len(text) > 4000:
        text = "📦 <b>Список товаров</b>\n\n" + "Выберите товар для управления:"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.as_markup(),
            parse_mode=ParseMode.HTML
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Сообщение уже содержит нужный текст, просто отвечаем
            await callback.answer("Список товаров обновлен")
        else:
            # Другая ошибка, пробрасываем её
            raise
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin:product:"))
async def product_actions(callback: CallbackQuery, product_repo: ProductRepository, category_repo: CategoryRepository):
    """Действия с товаром"""
    # Получаем ID товара
    product_id = callback.data.split(":")[-1]
    
    try:
        # Получаем товар
        product = await product_repo.get_product(product_id)
        
        if not product:
            try:
                await callback.message.edit_text(
                    "❌ Ошибка\n\n"
                    "Товар не найден.",
                    reply_markup=get_products_management_keyboard(),
                    parse_mode=ParseMode.HTML
                )
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    await callback.answer("Товар не найден")
                else:
                    raise
            await callback.answer()
            return
        
        # Получаем категорию
        category_name = "Без категории"
        if product.category_id:
            category = await category_repo.get_category(product.category_id)
            if category:
                category_name = category.name
        
        # Очищаем описание от некорректных HTML-тегов
        import re
        clean_description = product.description or 'Отсутствует'
        if clean_description != 'Отсутствует':
            # Удаляем все HTML-теги
            clean_description = re.sub(r'<[^>]+>', '', clean_description)
            # Экранируем специальные символы
            clean_description = clean_description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Формируем информацию о товаре
        product_info = (
            f"📦 Товар: {product.name}\n\n"
            f"📝 Описание: {clean_description}\n"
            f"💰 Цена: {product.price:.2f}₽\n"
            f"📂 Категория: {category_name}\n"
            f"🔢 Количество: {product.quantity} шт.\n"
            f"📊 Продано: {product.sales_count} шт.\n"
            f"🆔 ID: {product.id}\n"
            f"📅 Создан: {product.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )
        
        # Если есть изображение/инструкция, добавляем информацию о них
        if product.image_url:
            product_info += f"🖼 Изображение: Загружено\n"
        if product.instruction_link:
            product_info += f"📖 Инструкция: Установлена\n"
        if product.stars_enabled:
            product_info += f"✨ Оплата звездами: Включена ({product.stars_price or '—'} ⭐)\n"
        else:
            product_info += f"✨ Оплата звездами: Выключена\n"
        
        try:
            await callback.message.edit_text(
                product_info + "\nВыберите действие:",
                reply_markup=get_admin_product_actions_keyboard(str(product.id))
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer("Информация о товаре обновлена")
            else:
                raise
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении товара: {e}")
        try:
            await callback.message.edit_text(
                "❌ Ошибка\n\n"
                "Не удалось получить информацию о товаре.",
                reply_markup=get_products_management_keyboard(),
                parse_mode=ParseMode.HTML
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer("Произошла ошибка")
            else:
                raise
        await callback.answer()


# Управление позициями товаров

@router.callback_query(F.data.startswith("admin:add_items:"))
async def add_items_menu(callback: CallbackQuery, state: FSMContext):
    """Меню добавления позиций товара"""
    product_id = callback.data.split(":")[-1]
    
    await callback.message.edit_text(
        "📦 <b>Добавление позиций товара</b>\n\n"
        "Выберите способ добавления позиций:",
        reply_markup=get_add_items_method_keyboard(product_id),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:add_item_single:"))
async def add_item_single_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления одной позиции"""
    product_id = callback.data.split(":")[-1]
    
    # Сохраняем ID товара в состоянии
    await state.update_data(product_id=product_id)
    await state.set_state(ProductManagement.add_items)
    
    await callback.message.edit_text(
        "📝 <b>Добавление позиции товара</b>\n\n"
        "Введите данные позиции (например: логин:пароль, ключ активации и т.д.)\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(ProductManagement.add_items)
async def process_add_item_single(message: Message, state: FSMContext, product_item_repo: ProductItemRepository):
    """Обработка добавления одной позиции"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Добавление позиции отменено",
            reply_markup=get_products_management_keyboard()
        )
        return
    
    # Получаем ID товара из состояния
    data = await state.get_data()
    product_id = data.get("product_id")
    
    if not product_id:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Не найден ID товара. Попробуйте еще раз.",
            parse_mode=ParseMode.HTML
        )
        await state.clear()
        return
    
    item_data = message.text.strip()
    
    if not item_data:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Данные позиции не могут быть пустыми.\n"
            "Попробуйте еще раз или нажмите /cancel для отмены.",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        # Создаем позицию товара
        item = await product_item_repo.create_item(product_id, item_data)
        
        # Обновляем количество товара на основе позиций
        await product_item_repo.update_product_quantity_from_items(product_id)
        
        await message.answer(
            "✅ <b>Позиция добавлена</b>\n\n"
            f"Данные: <code>{item.data}</code>\n"
            f"ID: <code>{item.id}</code>\n\n"
            "Позиция готова к продаже!",
            reply_markup=get_items_management_keyboard(product_id),
            parse_mode=ParseMode.HTML
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении позиции: {e}")
        await message.answer(
            "❌ <b>Ошибка при добавлении позиции</b>\n\n"
            "Попробуйте еще раз позже или обратитесь к разработчику.",
            parse_mode=ParseMode.HTML
        )
        await state.clear()


@router.callback_query(F.data.startswith("admin:add_items_batch:"))
async def add_items_batch_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления позиций пакетом"""
    product_id = callback.data.split(":")[-1]
    
    # Сохраняем ID товара в состоянии
    await state.update_data(product_id=product_id)
    await state.set_state(ProductManagement.add_items_batch)
    
    await callback.message.edit_text(
        "📦 <b>Добавление позиций пакетом</b>\n\n"
        "Введите данные позиций, каждую с новой строки:\n\n"
        "Пример:\n"
        "<code>логин1:пароль1\n"
        "логин2:пароль2\n"
        "ключ1:активация1</code>\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(ProductManagement.add_items_batch)
async def process_add_items_batch(message: Message, state: FSMContext, product_item_repo: ProductItemRepository):
    """Обработка добавления позиций пакетом"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Добавление позиций отменено",
            reply_markup=get_products_management_keyboard()
        )
        return
    
    # Получаем ID товара из состояния
    data = await state.get_data()
    product_id = data.get("product_id")
    
    if not product_id:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Не найден ID товара. Попробуйте еще раз.",
            parse_mode=ParseMode.HTML
        )
        await state.clear()
        return
    
    # Разбиваем текст на строки
    items_data = [line.strip() for line in message.text.split('\n') if line.strip()]
    
    if not items_data:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Не найдены данные для добавления.\n"
            "Попробуйте еще раз или нажмите /cancel для отмены."
        )
        return
    
    try:
        # Создаем позиции товара
        created_items = await product_item_repo.create_multiple_items(product_id, items_data)
        
        # Обновляем количество товара на основе позиций
        await product_item_repo.update_product_quantity_from_items(product_id)
        
        await message.answer(
            "✅ <b>Позиции добавлены</b>\n\n"
            f"Добавлено позиций: <b>{len(created_items)}</b>\n\n"
            "Все позиции готовы к продаже!",
            reply_markup=get_items_management_keyboard(product_id),
            parse_mode=ParseMode.HTML
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении позиций: {e}")
        await message.answer(
            "❌ <b>Ошибка при добавлении позиций</b>\n\n"
            "Попробуйте еще раз позже или обратитесь к разработчику.",
            parse_mode=ParseMode.HTML
        )
        await state.clear()


@router.callback_query(F.data.startswith("admin:view_items:"))
async def view_items(callback: CallbackQuery, product_item_repo: ProductItemRepository):
    """Просмотр позиций товара"""
    product_id = callback.data.split(":")[-1]
    
    try:
        # Получаем все позиции товара
        items = await product_item_repo.get_all_items(product_id)
        available_count = await product_item_repo.count_available_items(product_id)
        total_count = await product_item_repo.count_total_items(product_id)
        
        if not items:
            await callback.message.edit_text(
                "📦 <b>Позиции товара</b>\n\n"
                "Позиции не найдены. Добавьте новые позиции.",
                reply_markup=get_items_management_keyboard(product_id),
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            return
        
        text = f"📦 <b>Позиции товара</b>\n\n"
        text += f"📊 Всего позиций: <b>{total_count}</b>\n"
        text += f"✅ Доступно: <b>{available_count}</b>\n"
        text += f"❌ Продано: <b>{total_count - available_count}</b>\n\n"
        
        # Показываем первые 10 позиций
        for i, item in enumerate(items[:10], 1):
            status = "✅" if not item.is_sold else "❌"
            text += f"{i}. {status} <code>{item.data}</code>\n"
        
        if len(items) > 10:
            text += f"\n... и еще <b>{len(items) - 10}</b> позиций"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_items_management_keyboard(product_id),
            parse_mode=ParseMode.HTML
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении позиций: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            "Не удалось получить информацию о позициях.",
            reply_markup=get_items_management_keyboard(product_id),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin:edit_product:"))
async def edit_product_start(callback: CallbackQuery, state: FSMContext, product_repo: ProductRepository):
    """Начало редактирования товара"""
    product_id = callback.data.split(":")[-1]
    
    # Сохраняем ID товара в состоянии
    await state.update_data(product_id=product_id)
    await state.set_state(ProductManagement.edit_product_name)
    
    # Получаем товар
    product = await product_repo.get_product(product_id)
    
    if not product:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            "Товар не найден.",
            reply_markup=get_products_management_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"📝 <b>Редактирование товара</b>\n\n"
        f"Текущее название: <b>{product.name}</b>\n\n"
        "Введите новое название товара или нажмите /cancel для отмены.",
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.message(ProductManagement.edit_product_name)
async def process_edit_product_name(message: Message, state: FSMContext):
    """Обработка ввода нового названия товара"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Редактирование товара отменено",
            reply_markup=get_products_management_keyboard()
        )
        return
    
    product_name = message.text.strip()
    
    if not product_name:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Название товара не может быть пустым.\n"
            "Попробуйте еще раз или нажмите /cancel для отмены.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Сохраняем новое название
    await state.update_data(new_product_name=product_name)
    
    # Переходим к редактированию описания
    await state.set_state(ProductManagement.edit_product_description)
    
    await message.answer(
        "📝 <b>Редактирование товара: описание</b>\n\n"
        "Введите новое описание товара.\n"
        "Можно использовать HTML-разметку.\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )


@router.message(ProductManagement.edit_product_description)
async def process_edit_product_description(message: Message, state: FSMContext):
    """Обработка ввода нового описания товара"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Редактирование товара отменено",
            reply_markup=get_products_management_keyboard()
        )
        return
    
    product_description = message.text.strip()
    
    # Сохраняем новое описание
    await state.update_data(new_product_description=product_description)
    
    # Переходим к редактированию цены
    await state.set_state(ProductManagement.edit_product_price)
    
    await message.answer(
        "💰 <b>Редактирование товара: цена</b>\n\n"
        "Введите новую цену товара в рублях.\n"
        "Например: <code>100</code> или <code>99.99</code>\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )


@router.message(ProductManagement.edit_product_price)
async def process_edit_product_price(message: Message, state: FSMContext, product_repo: ProductRepository):
    """Обработка ввода новой цены товара"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Редактирование товара отменено",
            reply_markup=get_products_management_keyboard()
        )
        return
    
    try:
        # Проверяем, не пришли ли мы сюда из сценария установки цены в звездах
        data = await state.get_data()
        if data.get("product_id") and data.get("set_stars_price"):
            stars_price = int(message.text.strip())
            if stars_price <= 0:
                await message.answer("❌ Цена в звездах должна быть положительным целым", parse_mode=ParseMode.HTML)
                return
            product = await product_repo.get_product(data.get("product_id"))
            if not product:
                await message.answer("❌ Товар не найден", parse_mode=ParseMode.HTML)
                await state.clear()
                return
            product.stars_enabled = True
            product.stars_price = stars_price
            await product_repo.update_product(product)
            await message.answer(
                f"✅ Оплата звездами включена: <b>{stars_price} ⭐</b>",
                reply_markup=get_admin_product_actions_keyboard(str(product.id)),
                parse_mode=ParseMode.HTML
            )
            await state.clear()
            return

        product_price = float(message.text.strip().replace(",", "."))
        
        if product_price <= 0:
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Цена товара должна быть положительным числом.\n"
                "Попробуйте еще раз или нажмите /cancel для отмены.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получаем данные из состояния
        data = await state.get_data()
        product_id = data.get("product_id")
        new_product_name = data.get("new_product_name")
        new_product_description = data.get("new_product_description")
        
        # Получаем товар
        product = await product_repo.get_product(product_id)
        
        if not product:
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Товар не найден.",
                parse_mode=ParseMode.HTML
            )
            await state.clear()
            return
        
        # Обновляем товар
        old_name = product.name
        old_description = product.description
        old_price = product.price
        
        product.name = new_product_name
        product.description = new_product_description
        product.price = product_price
        
        await product_repo.update_product(product)
        
        await message.answer(
            "✅ <b>Товар обновлен</b>\n\n"
            f"<b>Название:</b>\n"
            f"Было: {old_name}\n"
            f"Стало: {product.name}\n\n"
            f"<b>Описание:</b>\n"
            f"Было: {old_description or 'Отсутствует'}\n"
            f"Стало: {product.description or 'Отсутствует'}\n\n"
            f"<b>Цена:</b>\n"
            f"Было: {old_price:.2f}₽\n"
            f"Стало: {product.price:.2f}₽",
            reply_markup=get_admin_product_actions_keyboard(str(product.id)),
            parse_mode=ParseMode.HTML
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Введите корректное число.\n"
            "Попробуйте еще раз или нажмите /cancel для отмены.",
            parse_mode=ParseMode.HTML
        )


@router.callback_query(F.data.startswith("admin:upload_image:"))
async def upload_image_start(callback: CallbackQuery, state: FSMContext):
    """Начало загрузки изображения товара"""
    product_id = callback.data.split(":")[-1]
    
    # Сохраняем ID товара в состоянии
    await state.update_data(product_id=product_id)
    await state.set_state(ProductManagement.upload_image)
    
    await callback.message.edit_text(
        "🖼 <b>Загрузка изображения товара</b>\n\n"
        "Отправьте изображение для товара.\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin:set_instruction:"))
async def set_instruction_start(callback: CallbackQuery, state: FSMContext):
    """Начало установки ссылки на инструкцию"""
    product_id = callback.data.split(":")[-1]
    await state.update_data(product_id=product_id)
    await state.set_state(ProductManagement.edit_product_instruction)
    await callback.message.edit_text(
        "📖 <b>Ссылка на инструкцию</b>\n\n"
        "Отправьте полную ссылку (URL) на инструкцию для покупателя.\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:stars:on:"))
async def stars_on_start(callback: CallbackQuery, state: FSMContext, product_repo: ProductRepository):
    product_id = callback.data.split(":")[-1]
    await state.update_data(product_id=product_id, set_stars_price=True)
    await state.set_state(ProductManagement.edit_product_price)
    await callback.message.edit_text(
        "✨ <b>Включение оплаты звездами</b>\n\n"
        "Укажите цену в звездах (целое число).\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:stars:off:"))
async def stars_off(callback: CallbackQuery, product_repo: ProductRepository):
    product_id = callback.data.split(":")[-1]
    product = await product_repo.get_product(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return
    product.stars_enabled = False
    product.stars_price = None
    await product_repo.update_product(product)
    await callback.message.edit_text(
        "✨ Оплата звездами выключена",
        reply_markup=get_admin_product_actions_keyboard(str(product.id))
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete_product:"))
async def delete_product_confirm(callback: CallbackQuery, state: FSMContext, product_repo: ProductRepository):
    """Подтверждение удаления товара"""
    # Получаем ID товара
    product_id = callback.data.split(":")[-1]
    
    # Сохраняем ID товара в состоянии
    await state.update_data(product_id=product_id)
    await state.set_state(ProductManagement.delete_product_confirm)
    
    # Получаем товар
    product = await product_repo.get_product(product_id)
    
    if not product:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            "Товар не найден.",
            reply_markup=get_products_management_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        await state.clear()
        return
    
    # Создаем клавиатуру для подтверждения
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin:delete_product_confirm:{product_id}"),
        InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"admin:product:{product_id}")
    )
    
    await callback.message.edit_text(
        f"❓ <b>Подтверждение удаления</b>\n\n"
        f"Вы действительно хотите удалить товар <b>{product.name}</b>?\n\n"
        f"📦 Товар: {product.name}\n"
        f"💰 Цена: {product.price:.2f}₽\n"
        f"🔢 Количество: {product.quantity} шт.\n"
        f"📊 Продано: {product.sales_count} шт.\n\n"
        "⚠️ Внимание! Это действие нельзя отменить!",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete_product_confirm:"))
async def delete_product_process(callback: CallbackQuery, state: FSMContext, product_repo: ProductRepository, product_item_repo: ProductItemRepository):
    """Процесс удаления товара"""
    # Получаем ID товара
    product_id = callback.data.split(":")[-1]
    
    try:
        # Получаем товар
        product = await product_repo.get_product(product_id)
        
        if not product:
            await callback.message.edit_text(
                "❌ <b>Ошибка</b>\n\n"
                "Товар не найден.",
                reply_markup=get_products_management_keyboard(),
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            await state.clear()
            return
        
        # Сохраняем информацию о товаре для отчета
        product_name = product.name
        product_price = product.price
        product_quantity = product.quantity
        product_sales = product.sales_count
        
        # Удаляем все позиции товара
        await product_item_repo.delete_items_by_product(product_id)
        
        # Удаляем товар
        result = await product_repo.delete_product(product_id)
        
        if result:
            await callback.message.edit_text(
                "✅ <b>Товар удален</b>\n\n"
                f"Товар <b>{product_name}</b> успешно удален.\n\n"
                f"📦 Название: {product_name}\n"
                f"💰 Цена: {product_price:.2f}₽\n"
                f"🔢 Количество: {product_quantity} шт.\n"
                f"📊 Продано: {product_sales} шт.\n\n"
                "Все позиции товара также были удалены.",
                reply_markup=get_products_management_keyboard(),
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.edit_text(
                "❌ <b>Ошибка</b>\n\n"
                "Не удалось удалить товар.",
                reply_markup=get_products_management_keyboard(),
                parse_mode=ParseMode.HTML
            )
        
        await callback.answer()
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при удалении товара: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка при удалении товара</b>\n\n"
            "Попробуйте еще раз позже или обратитесь к разработчику.",
            reply_markup=get_products_management_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        await state.clear()

@router.message(ProductManagement.edit_product_instruction)
async def set_instruction_process(message: Message, state: FSMContext, product_repo: ProductRepository):
    """Сохраняем ссылку на инструкцию"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Установка ссылки отменена", reply_markup=get_products_management_keyboard())
        return
    data = await state.get_data()
    product_id = data.get("product_id")
    if not product_id:
        await message.answer("❌ Ошибка: не найден ID товара", parse_mode=ParseMode.HTML)
        await state.clear()
        return
    url = message.text.strip()
    product = await product_repo.get_product(product_id)
    if not product:
        await message.answer("❌ Товар не найден", parse_mode=ParseMode.HTML)
        await state.clear()
        return
    product.instruction_link = url
    await product_repo.update_product(product)
    await message.answer(
        "✅ <b>Ссылка на инструкцию сохранена</b>",
        reply_markup=get_admin_product_actions_keyboard(str(product.id)),
        parse_mode=ParseMode.HTML
    )
    await state.clear()

@router.message(ProductManagement.upload_image, F.photo)
async def process_upload_image(message: Message, state: FSMContext, product_repo: ProductRepository):
    """Обработка загрузки изображения товара"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Загрузка изображения отменена",
            reply_markup=get_products_management_keyboard()
        )
        return
    
    # Получаем ID товара из состояния
    data = await state.get_data()
    product_id = data.get("product_id")
    
    if not product_id:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Не найден ID товара. Попробуйте еще раз.",
            parse_mode=ParseMode.HTML
        )
        await state.clear()
        return
    
    try:
        # Получаем товар
        product = await product_repo.get_product(product_id)
        
        if not product:
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Товар не найден.",
                parse_mode=ParseMode.HTML
            )
            await state.clear()
            return
        
        # Получаем информацию о фото
        photo = message.photo[-1]  # Берем самое большое фото
        
        # В будущем здесь будет загрузка в CDN
        # Пока просто сохраняем file_id
        product.image_url = photo.file_id
        await product_repo.update_product(product)
        
        await message.answer(
            "✅ <b>Изображение загружено</b>\n\n"
            f"Изображение успешно добавлено к товару <b>{product.name}</b>.\n\n"
            "В будущем изображения будут храниться в CDN.",
            reply_markup=get_admin_product_actions_keyboard(str(product.id)),
            parse_mode=ParseMode.HTML
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке изображения: {e}")
        await message.answer(
            "❌ <b>Ошибка при загрузке изображения</b>\n\n"
            "Попробуйте еще раз позже или обратитесь к разработчику.",
            parse_mode=ParseMode.HTML
        )
        await state.clear()


@router.message(ProductManagement.upload_image)
async def process_upload_image_text(message: Message, state: FSMContext):
    """Обработка текста вместо изображения"""
    await message.answer(
        "❌ <b>Ошибка</b>\n\n"
        "Пожалуйста, отправьте изображение, а не текст.\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )