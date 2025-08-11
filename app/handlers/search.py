from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from loguru import logger
from bson import ObjectId

from app.filters.admin import AdminFilter
from app.states.admin_states import UserSearch
from app.keyboards import get_search_keyboard
from app.database.repositories import UserRepository, TransactionRepository, ProductRepository


router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(Command("search"))
async def cmd_search(message: Message):
    """Обработчик команды поиска (только для администраторов)"""
    await message.answer(
        "🔍 <b>Поиск пользователя или чека</b>\n\n"
        "Выберите тип поиска:",
        reply_markup=get_search_keyboard(),
        parse_mode=ParseMode.HTML
    )


@router.message(F.text == "🔍 Поиск по ID пользователя")
async def search_by_user_id(message: Message, state: FSMContext):
    """Поиск пользователя по ID"""
    await state.set_state(UserSearch.enter_user_id)
    await message.answer(
        "🔍 <b>Поиск по ID пользователя</b>\n\n"
        "Отправьте ID пользователя для поиска.\n"
        "Например: <code>1257601441</code>\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )


@router.message(F.text == "🧾 Поиск по номеру чека")
async def search_by_receipt(message: Message, state: FSMContext):
    """Поиск чека по номеру"""
    await state.set_state(UserSearch.enter_receipt_id)
    await message.answer(
        "🧾 <b>Поиск по номеру чека</b>\n\n"
        "Отправьте номер чека для поиска.\n"
        "Например: <code>1110685899966612</code>\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )


@router.message(F.text == "🔙 Назад")
async def back_to_admin_panel(message: Message):
    """Возврат в админ-панель"""
    from app.handlers.admin_panel import cmd_admin_panel
    await cmd_admin_panel(message)


@router.message(UserSearch.enter_user_id)
async def process_user_id(message: Message, state: FSMContext, user_repo: UserRepository, transaction_repo: TransactionRepository):
    """Обработка введенного ID пользователя"""
    user_id = message.text.strip()
    
    if user_id == "/cancel":
        await state.clear()
        await message.answer("❌ Поиск отменен")
        return
    
    try:
        user_id = int(user_id)
        user = await user_repo.get_user(user_id)
        
        if not user:
            await message.answer(
                "❌ <b>Пользователь не найден</b>\n\n"
                f"Пользователь с ID <code>{user_id}</code> не найден в базе данных.\n\n"
                "Попробуйте еще раз или нажмите /cancel для отмены",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получаем транзакции пользователя
        transactions = await transaction_repo.get_user_transactions(user_id, limit=5)
        
        # Создаем клавиатуру для управления пользователем
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Изменить баланс", callback_data=f"admin:edit_balance:{user.user_id}"),
                InlineKeyboardButton(text="💰 Выдать баланс", callback_data=f"admin:give_balance:{user.user_id}")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="admin:search_back")
            ]
        ])
        
        # Формируем информацию о пользователе
        user_info = (
            f"👤 <b>Информация о пользователе</b>\n\n"
            f"🆔 ID: <code>{user.user_id}</code>\n"
            f"👤 Логин: @{user.username or 'отсутствует'}\n"
            f"👤 Имя: {user.first_name or 'не указано'}\n"
            f"💰 Баланс: <b>{user.balance:.2f}₽</b>\n"
            f"🛒 Куплено товаров: <b>{user.purchases}шт</b>\n"
            f"👑 Администратор: <b>{'✅ Да' if user.is_admin else '❌ Нет'}</b>\n\n"
            f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')}\n"
            f"📅 Последняя активность: {user.last_active.strftime('%d.%m.%Y %H:%M:%S')}\n\n"
        )
        
        # Добавляем информацию о последних транзакциях
        if transactions:
            user_info += "<b>Последние транзакции:</b>\n"
            for tx in transactions:
                tx_type = "💰 Пополнение" if tx.type == "deposit" else "🛒 Покупка"
                tx_status = {
                    "pending": "⏳ В ожидании",
                    "completed": "✅ Выполнено",
                    "canceled": "❌ Отменено"
                }.get(tx.status, tx.status)
                
                user_info += (
                    f"- {tx_type}: {tx.amount:.2f}₽ ({tx_status})\n"
                    f"  Дата: {tx.created_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
                )
                
                if tx.receipt_id:
                    user_info += f"  Чек: <code>{tx.receipt_id}</code>\n"
                
                user_info += "\n"
        else:
            user_info += "<b>Транзакции отсутствуют</b>"
        
        await message.answer(user_info, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат ID</b>\n\n"
            "ID пользователя должен быть числом.\n\n"
            "Попробуйте еще раз или нажмите /cancel для отмены",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка при поиске пользователя: {e}")
        await message.answer(
            "❌ <b>Произошла ошибка при поиске пользователя</b>\n\n"
            "Попробуйте еще раз позже или обратитесь к разработчику.",
            parse_mode=ParseMode.HTML
        )
        await state.clear()


@router.message(UserSearch.enter_receipt_id)
async def process_receipt_id(message: Message, state: FSMContext, transaction_repo: TransactionRepository, user_repo: UserRepository, product_repo: ProductRepository):
    """Обработка введенного номера чека"""
    receipt_id = message.text.strip()
    
    if receipt_id == "/cancel":
        await state.clear()
        await message.answer("❌ Поиск отменен")
        return
    
    try:
        # Ищем транзакцию по номеру чека
        transaction = await transaction_repo.get_transaction_by_receipt(receipt_id)
        
        if not transaction:
            await message.answer(
                "❌ <b>Чек не найден</b>\n\n"
                f"Чек с номером <code>{receipt_id}</code> не найден в базе данных.\n\n"
                "Попробуйте еще раз или нажмите /cancel для отмены",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получаем информацию о пользователе
        user = await user_repo.get_user(transaction.user_id)
        
        # Получаем информацию о товаре, если это покупка
        product_info = ""
        if transaction.type == "purchase" and transaction.product_id:
            product = await product_repo.get_product(transaction.product_id)
            if product:
                product_info = (
                    f"📦 Название товара: <b>{product.name}</b>\n"
                    f"📝 Описание: {product.description or 'Отсутствует'}\n"
                    f"💰 Цена товара: <b>{product.price:.2f}₽</b>\n\n"
                )
        
        # Формируем информацию о чеке
        tx_type = "💰 Пополнение" if transaction.type == "deposit" else "🛒 Покупка"
        tx_status = {
            "pending": "⏳ В ожидании",
            "completed": "✅ Выполнено",
            "canceled": "❌ Отменено"
        }.get(transaction.status, transaction.status)
        
        receipt_info = (
            f"🧾 <b>Информация о чеке</b>\n\n"
            f"🆔 Номер чека: <code>{receipt_id}</code>\n"
            f"👤 Пользователь: <b>{user.first_name or 'Неизвестно'}</b> | <code>{user.user_id}</code>\n"
            f"💰 Сумма: <b>{transaction.amount:.2f}₽</b>\n"
            f"📋 Тип: <b>{tx_type}</b>\n"
            f"📊 Статус: <b>{tx_status}</b>\n"
            f"📅 Дата: {transaction.created_at.strftime('%d.%m.%Y %H:%M:%S')}\n\n"
        )
        
        # Добавляем информацию о товаре, если есть
        if product_info:
            receipt_info += f"{product_info}"
        
        # Добавляем информацию о способе оплаты, если есть
        if transaction.payment_method:
            receipt_info += f"💳 Способ оплаты: <b>{transaction.payment_method}</b>\n"
        
        # Добавляем информацию о платеже, если есть
        if transaction.payment_id:
            receipt_info += f"🆔 ID платежа: <code>{transaction.payment_id}</code>\n"
        
        await message.answer(receipt_info, parse_mode=ParseMode.HTML)
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при поиске чека: {e}")
        await message.answer(
            "❌ <b>Произошла ошибка при поиске чека</b>\n\n"
            "Попробуйте еще раз позже или обратитесь к разработчику.",
            parse_mode=ParseMode.HTML
        )
        await state.clear()