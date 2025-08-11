from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from loguru import logger
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from app.database.repositories import UserRepository, ProductRepository, TransactionRepository, ProductItemRepository
from app.keyboards import get_main_keyboard
from app.filters.admin import AdminFilter
from app.config import Config


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, user_repo: UserRepository, config: Config):
    """Обработчик команды /start"""
    user = await user_repo.get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Проверяем, является ли пользователь администратором
    is_admin = message.from_user.id in config.bot.admin_ids
    
    # Если пользователь админ, устанавливаем флаг в базе данных
    if is_admin and not user.is_admin:
        user.is_admin = True
        await user_repo.update_user(user)
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Добро пожаловать в магазин Siriushop!\n"
        "Используйте кнопки ниже для навигации:",
        reply_markup=get_main_keyboard(is_admin),
        parse_mode=ParseMode.HTML
    )


@router.message(Command("profile"))
@router.message(F.text == "👤 Профиль")
async def cmd_profile(message: Message, user_repo: UserRepository, config: Config):
    """Обработчик команды профиля"""
    user = await user_repo.get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ Ваш профиль не найден. Используйте /start для регистрации.", parse_mode=ParseMode.HTML)
        return
    
    # Проверяем, является ли пользователь администратором
    is_admin = message.from_user.id in config.bot.admin_ids
    admin_status = "✅ Да" if is_admin else "❌ Нет"
    
    # Создаем клавиатуру для профиля
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Покупки", callback_data="profile:purchases")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="profile:refresh")
        ]
    ])
    
    await message.answer(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user.user_id}</code>\n"
        f"💰 Баланс: <b>{user.balance:.2f}₽</b>\n"
        f"🛒 Куплено товаров: <b>{user.purchases}шт</b>\n"
        f"👑 Администратор: <b>{admin_status}</b>\n\n"
        f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')} ({(datetime.now() - user.created_at).days} дней)",
        reply_markup=keyboard if is_admin else None,
        parse_mode=ParseMode.HTML
    )


@router.message(F.text == "📦 Наличие товаров")
async def cmd_products(message: Message, product_repo: ProductRepository, state: FSMContext):
    """Обработчик команды наличия товаров с пагинацией"""
    products = await product_repo.get_all_products(available_only=True)
    if not products:
        await message.answer("❌ В данный момент товары отсутствуют.", parse_mode=ParseMode.HTML)
        return
    page = 1
    per_page = 10
    await state.update_data(products_page=page)
    total = len(products)
    items = products[(page-1)*per_page: page*per_page]
    text = "\n".join([f"• <b>{p.name}</b> - {p.price:.2f}₽ ({p.quantity} шт.)" for p in items])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏮️", callback_data="products:first"),
         InlineKeyboardButton(text="◀️", callback_data="products:prev"),
         InlineKeyboardButton(text=f"{page}/{(total-1)//per_page+1}", callback_data="noop"),
         InlineKeyboardButton(text="▶️", callback_data="products:next"),
         InlineKeyboardButton(text="⏭️", callback_data="products:last")]
    ])
    await message.answer(
        "📦 <b>Доступные товары:</b>\n\n" + text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.regexp(r"^products:(first|prev|next|last)$"))
async def paginate_products(callback: CallbackQuery, state: FSMContext, product_repo: ProductRepository):
    products = await product_repo.get_all_products(available_only=True)
    if not products:
        await callback.answer("❌ Нет товаров", show_alert=True)
        return
    data = await state.get_data()
    page = int(data.get("products_page", 1))
    per_page = 10
    pages = max(1, (len(products)-1)//per_page + 1)
    action = callback.data.split(":")[1]
    old_page = page
    if action == "first":
        page = 1
    elif action == "prev":
        page = max(1, page-1)
    elif action == "next":
        page = min(pages, page+1)
    elif action == "last":
        page = pages
    # Если страница не изменилась — просто уведомляем и выходим
    if page == old_page:
        await callback.answer("Это крайняя страница")
        return
    await state.update_data(products_page=page)
    items = products[(page-1)*per_page: page*per_page]
    text = "\n".join([f"• <b>{p.name}</b> - {p.price:.2f}₽ ({p.quantity} шт.)" for p in items])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏮️", callback_data="products:first"),
         InlineKeyboardButton(text="◀️", callback_data="products:prev"),
         InlineKeyboardButton(text=f"{page}/{pages}", callback_data="noop"),
         InlineKeyboardButton(text="▶️", callback_data="products:next"),
         InlineKeyboardButton(text="⏭️", callback_data="products:last")]
    ])
    try:
        await callback.message.edit_text(
            "📦 <b>Доступные товары:</b>\n\n" + text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    except TelegramBadRequest:
        await callback.answer()
    await callback.answer()


@router.message(F.text == "📞 Поддержка")
async def cmd_support(message: Message):
    """Обработчик команды поддержки"""
    # Создаем клавиатуру с кнопкой перехода к поддержке
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Написать в поддержку", url="https://t.me/Siriusatop123")]
    ])
    
    await message.answer(
        "📞 <b>Поддержка</b>\n\n"
        "Если у вас возникли вопросы или проблемы, напишите нам:\n"
        "Мы ответим вам в ближайшее время!",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.message(F.text == "📊 Финансы и статистика")
@router.message(Command("stats"))
async def cmd_stats(message: Message, user_repo: UserRepository, config: Config):
    """Обработчик команды статистики (только для администраторов)"""
    logger.info(f"Пользователь {message.from_user.id} нажал кнопку статистики")
    
    # Проверяем, является ли пользователь администратором
    if message.from_user.id not in config.bot.admin_ids:
        logger.info(f"Пользователь {message.from_user.id} не является администратором")
        return
    
    # Создаем клавиатуру для статистики
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика за день", callback_data="stats:day"),
            InlineKeyboardButton(text="📊 Статистика за неделю", callback_data="stats:week")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика за месяц", callback_data="stats:month"),
            InlineKeyboardButton(text="📈 Популярные товары", callback_data="stats:popular")
        ],
        [
            InlineKeyboardButton(text="💰 История пополнений", callback_data="stats:deposits"),
            InlineKeyboardButton(text="🛒 История покупок", callback_data="stats:purchases")
        ]
    ])
    
    await message.answer(
        "📊 <b>Финансы и статистика</b>\n\n"
        "Выберите интересующий вас раздел:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


# Обработчики для callback-кнопок статистики
@router.callback_query(F.data == "stats:day")
async def stats_day(callback: CallbackQuery, transaction_repo: TransactionRepository):
    """Статистика за день"""
    stats = await transaction_repo.get_statistics_by_period(1)
    
    text = "📊 <b>Статистика за день</b>\n\n"
    text += f"🛒 <b>Покупки:</b>\n"
    text += f"   • Количество: <b>{stats['purchases']['count']}шт</b>\n"
    text += f"   • Сумма: <b>{stats['purchases']['amount']:.2f}₽</b>\n\n"
    text += f"💰 <b>Пополнения:</b>\n"
    text += f"   • Количество: <b>{stats['deposit']['count']}шт</b>\n"
    text += f"   • Сумма: <b>{stats['deposit']['amount']:.2f}₽</b>\n\n"
    text += f"📈 <b>Итого:</b>\n"
    text += f"   • Транзакций: <b>{stats['purchases']['count'] + stats['deposit']['count']}шт</b>\n"
    text += f"   • Общая сумма: <b>{stats['purchases']['amount'] + stats['deposit']['amount']:.2f}₽</b>"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="stats:back")]
        ]),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "stats:week")
async def stats_week(callback: CallbackQuery, transaction_repo: TransactionRepository):
    """Статистика за неделю"""
    stats = await transaction_repo.get_statistics_by_period(7)
    
    text = "📊 <b>Статистика за неделю</b>\n\n"
    text += f"🛒 <b>Покупки:</b>\n"
    text += f"   • Количество: <b>{stats['purchases']['count']}шт</b>\n"
    text += f"   • Сумма: <b>{stats['purchases']['amount']:.2f}₽</b>\n\n"
    text += f"💰 <b>Пополнения:</b>\n"
    text += f"   • Количество: <b>{stats['deposit']['count']}шт</b>\n"
    text += f"   • Сумма: <b>{stats['deposit']['amount']:.2f}₽</b>\n\n"
    text += f"📈 <b>Итого:</b>\n"
    text += f"   • Транзакций: <b>{stats['purchases']['count'] + stats['deposit']['count']}шт</b>\n"
    text += f"   • Общая сумма: <b>{stats['purchases']['amount'] + stats['deposit']['amount']:.2f}₽</b>"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="stats:back")]
        ]),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "stats:month")
async def stats_month(callback: CallbackQuery, transaction_repo: TransactionRepository):
    """Статистика за месяц"""
    stats = await transaction_repo.get_statistics_by_period(30)
    
    text = "📊 <b>Статистика за месяц</b>\n\n"
    text += f"🛒 <b>Покупки:</b>\n"
    text += f"   • Количество: <b>{stats['purchases']['count']}шт</b>\n"
    text += f"   • Сумма: <b>{stats['purchases']['amount']:.2f}₽</b>\n\n"
    text += f"💰 <b>Пополнения:</b>\n"
    text += f"   • Количество: <b>{stats['deposit']['count']}шт</b>\n"
    text += f"   • Сумма: <b>{stats['deposit']['amount']:.2f}₽</b>\n\n"
    text += f"📈 <b>Итого:</b>\n"
    text += f"   • Транзакций: <b>{stats['purchases']['count'] + stats['deposit']['count']}шт</b>\n"
    text += f"   • Общая сумма: <b>{stats['purchases']['amount'] + stats['deposit']['amount']:.2f}₽</b>"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="stats:back")]
        ]),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "stats:popular")
async def stats_popular(callback: CallbackQuery, transaction_repo: TransactionRepository, product_repo: ProductRepository):
    """Популярные товары"""
    popular_stats = await transaction_repo.get_popular_products_stats(5)
    
    text = "📈 <b>Популярные товары</b>\n\n"
    
    if not popular_stats:
        text += "📝 Пока нет данных о покупках товаров"
    else:
        for i, item in enumerate(popular_stats, 1):
            product_id = item["_id"]
            product = await product_repo.get_product(product_id)
            product_name = product.name if product else f"Товар #{product_id}"
            
            text += f"{i}. <b>{product_name}</b>\n"
            text += f"   • Покупок: <b>{item['purchase_count']}шт</b>\n"
            text += f"   • Сумма: <b>{item['total_amount']:.2f}₽</b>\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="stats:back")]
        ]),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "stats:deposits")
async def stats_deposits(callback: CallbackQuery, transaction_repo: TransactionRepository):
    """История пополнений"""
    deposits = await transaction_repo.get_user_transactions(
        user_id=callback.from_user.id,
        transaction_type="deposit",
        limit=10
    )
    
    text = "💰 <b>История пополнений</b>\n\n"
    
    if not deposits:
        text += "📝 У вас пока нет пополнений"
    else:
        for deposit in deposits:
            text += (
                f"💳 <b>Пополнение #{deposit.receipt_id}</b>\n"
                f"💰 Сумма: <b>{deposit.amount:.2f}₽</b>\n"
                f"📅 Дата: {deposit.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"✅ Статус: <b>{'Оплачено' if deposit.status == 'completed' else 'В обработке'}</b>\n\n"
            )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="stats:back")]
        ]),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "stats:purchases")
async def stats_purchases(callback: CallbackQuery, transaction_repo: TransactionRepository):
    """История покупок"""
    purchases = await transaction_repo.get_user_transactions(
        user_id=callback.from_user.id,
        transaction_type="purchase",
        limit=10
    )
    
    text = "🛒 <b>История покупок</b>\n\n"
    
    if not purchases:
        text += "📝 У вас пока нет покупок"
    else:
        for purchase in purchases:
            text += (
                f"🧾 <b>Покупка #{purchase.receipt_id}</b>\n"
                f"💰 Сумма: <b>{purchase.amount:.2f}₽</b>\n"
                f"📅 Дата: {purchase.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"✅ Статус: <b>{'Оплачено' if purchase.status == 'completed' else 'В обработке'}</b>\n\n"
            )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="stats:back")]
        ]),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "stats:back")
async def stats_back(callback: CallbackQuery, config: Config):
    """Возврат к главному меню статистики"""
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in config.bot.admin_ids:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Создаем клавиатуру для статистики
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика за день", callback_data="stats:day"),
            InlineKeyboardButton(text="📊 Статистика за неделю", callback_data="stats:week")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика за месяц", callback_data="stats:month"),
            InlineKeyboardButton(text="📈 Популярные товары", callback_data="stats:popular")
        ],
        [
            InlineKeyboardButton(text="💰 История пополнений", callback_data="stats:deposits"),
            InlineKeyboardButton(text="🛒 История покупок", callback_data="stats:purchases")
        ]
    ])
    
    await callback.message.edit_text(
        "📊 <b>Финансы и статистика</b>\n\n"
        "Выберите интересующий вас раздел:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "profile:purchases")
async def show_purchases(callback: CallbackQuery, user_repo: UserRepository, transaction_repo: TransactionRepository, state: FSMContext):
    """Показать историю покупок пользователя"""
    user = await user_repo.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Инициализация страницы
    await state.update_data(purchases_page=1)
    page = 1
    per_page = 5
    # Получаем транзакции покупок пользователя
    transactions = await transaction_repo.get_user_transactions(
        user_id=callback.from_user.id,
        transaction_type="purchase",
        limit=100
    )
    
    if not transactions:
        # Создаем клавиатуру для возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к профилю", callback_data="profile:back")]
        ])
        
        await callback.message.edit_text(
            "🛒 <b>Ваши покупки:</b>\n\n"
            "📝 У вас пока нет покупок.\n"
            "Совершите первую покупку, чтобы увидеть историю!",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    
    # Формируем текст с историей покупок
    text = "🛒 <b>Ваши покупки:</b>\n\n"
    
    pages = max(1, (len(transactions)-1)//per_page + 1)
    rows = []
    for transaction in transactions[(page-1)*per_page: page*per_page]:
        text += (
            f"🧾 <b>Чек #{transaction.receipt_id}</b>\n"
            f"💰 Сумма: <b>{transaction.amount:.2f}₽</b>\n"
            f"📅 Дата: {transaction.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"✅ Статус: <b>{'Оплачено' if transaction.status == 'completed' else 'В обработке'}</b>\n"
        )
        # кнопка на повторную выдачу данных по чеку
        rows.append([InlineKeyboardButton(text=f"Показать данные по чеку {transaction.receipt_id}", callback_data=f"profile:receipt:{transaction.receipt_id}")])
        text += "\n"
    
    # Клавиатура с пагинацией
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏮️", callback_data="profile:purchases:first"),
         InlineKeyboardButton(text="◀️", callback_data="profile:purchases:prev"),
         InlineKeyboardButton(text=f"{page}/{pages}", callback_data="noop"),
         InlineKeyboardButton(text="▶️", callback_data="profile:purchases:next"),
         InlineKeyboardButton(text="⏭️", callback_data="profile:purchases:last")],
        *rows,
        [InlineKeyboardButton(text="🔙 Назад к профилю", callback_data="profile:back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("profile:receipt:"))
async def resend_purchase_data(callback: CallbackQuery, product_item_repo: ProductItemRepository, product_repo: ProductRepository):
    """Повторно отправить данные покупки по номеру чека"""
    receipt_id = callback.data.split(":")[-1]
    items = await product_item_repo.get_items_by_receipt(receipt_id, user_id=callback.from_user.id)
    if not items:
        await callback.answer("Данные по чеку не найдены", show_alert=True)
        return
    for item in items:
        instruction = ""
        try:
            product = await product_repo.get_product(item.product_id)
            if product and product.instruction_link:
                instruction = f"\n\n📖 <b>Инструкция:</b> <a href='{product.instruction_link}'>Ссылка</a>"
        except Exception:
            pass
        await callback.message.answer(
            f"📦 <b>Данные по чеку {receipt_id}:</b>\n<code>{item.data}</code>" + instruction,
            parse_mode=ParseMode.HTML
        )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^profile:purchases:(first|prev|next|last)$"))
async def paginate_purchases(callback: CallbackQuery, transaction_repo: TransactionRepository, state: FSMContext):
    data = await state.get_data()
    page = int(data.get("purchases_page", 1))
    per_page = 5
    transactions = await transaction_repo.get_user_transactions(
        user_id=callback.from_user.id,
        transaction_type="purchase",
        limit=100
    )
    if not transactions:
        await callback.answer("❌ Нет покупок", show_alert=True)
        return
    pages = max(1, (len(transactions)-1)//per_page + 1)
    action = callback.data.split(":")[-1]
    old_page = page
    if action == "first":
        page = 1
    elif action == "prev":
        page = max(1, page-1)
    elif action == "next":
        page = min(pages, page+1)
    elif action == "last":
        page = pages
    # Если страница не изменилась — просто уведомляем и выходим
    if page == old_page:
        await callback.answer("Это крайняя страница")
        return
    await state.update_data(purchases_page=page)
    text = "🛒 <b>Ваши покупки:</b>\n\n"
    rows = []
    for transaction in transactions[(page-1)*per_page: page*per_page]:
        text += (
            f"🧾 <b>Чек #{transaction.receipt_id}</b>\n"
            f"💰 Сумма: <b>{transaction.amount:.2f}₽</b>\n"
            f"📅 Дата: {transaction.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"✅ Статус: <b>{'Оплачено' if transaction.status == 'completed' else 'В обработке'}</b>\n"
        )
        rows.append([InlineKeyboardButton(text=f"Показать данные по чеку {transaction.receipt_id}", callback_data=f"profile:receipt:{transaction.receipt_id}")])
        text += "\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏮️", callback_data="profile:purchases:first"),
         InlineKeyboardButton(text="◀️", callback_data="profile:purchases:prev"),
         InlineKeyboardButton(text=f"{page}/{pages}", callback_data="noop"),
         InlineKeyboardButton(text="▶️", callback_data="profile:purchases:next"),
         InlineKeyboardButton(text="⏭️", callback_data="profile:purchases:last")],
         *rows,
         [InlineKeyboardButton(text="🔙 Назад к профилю", callback_data="profile:back")]
    ])
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except TelegramBadRequest:
        await callback.answer()
    await callback.answer()


@router.callback_query(F.data == "profile:refresh")
async def refresh_profile(callback: CallbackQuery, user_repo: UserRepository, config: Config):
    """Обновить профиль пользователя"""
    user = await user_repo.get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверяем, является ли пользователь администратором
    is_admin = callback.from_user.id in config.bot.admin_ids
    admin_status = "✅ Да" if is_admin else "❌ Нет"
    
    # Создаем клавиатуру для профиля
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Покупки", callback_data="profile:purchases")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="profile:refresh")
        ]
    ])
    
    try:
        await callback.message.edit_text(
            f"👤 <b>Ваш профиль</b>\n\n"
            f"🆔 ID: <code>{user.user_id}</code>\n"
            f"💰 Баланс: <b>{user.balance:.2f}₽</b>\n"
            f"🛒 Куплено товаров: <b>{user.purchases}шт</b>\n"
            f"👑 Администратор: <b>{admin_status}</b>\n\n"
            f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')} ({(datetime.now() - user.created_at).days} дней)",
            reply_markup=keyboard if is_admin else None,
            parse_mode=ParseMode.HTML
        )
        await callback.answer("✅ Профиль обновлен")
    except Exception as e:
        # Если сообщение не изменилось, просто показываем уведомление
        await callback.answer("✅ Профиль актуален")


@router.callback_query(F.data == "profile:back")
async def back_to_profile(callback: CallbackQuery, user_repo: UserRepository, config: Config):
    """Возврат к профилю"""
    user = await user_repo.get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Проверяем, является ли пользователь администратором
    is_admin = callback.from_user.id in config.bot.admin_ids
    admin_status = "✅ Да" if is_admin else "❌ Нет"
    
    # Создаем клавиатуру для профиля
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Покупки", callback_data="profile:purchases")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="profile:refresh")
        ]
    ])
    
    await callback.message.edit_text(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user.user_id}</code>\n"
        f"💰 Баланс: <b>{user.balance:.2f}₽</b>\n"
        f"🛒 Куплено товаров: <b>{user.purchases}шт</b>\n"
        f"👑 Администратор: <b>{admin_status}</b>\n\n"
        f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')} ({(datetime.now() - user.created_at).days} дней)",
        reply_markup=keyboard if is_admin else None,
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()