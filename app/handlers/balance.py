from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from loguru import logger

from app.filters.admin import AdminFilter
from app.states.admin_states import BalanceManagement
from app.database.repositories import UserRepository


router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.callback_query(F.data.startswith("admin:edit_balance:"))
async def edit_balance(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки изменения баланса"""
    # Получаем ID пользователя из callback_data
    user_id = int(callback.data.split(":")[-1])
    
    # Сохраняем ID пользователя в состоянии
    await state.update_data(user_id=user_id)
    
    # Переходим к состоянию ввода нового баланса
    await state.set_state(BalanceManagement.enter_new_balance)
    
    await callback.message.answer(
        "💳 <b>Изменение баланса пользователя</b>\n\n"
        f"Пользователь: <code>{user_id}</code>\n\n"
        "Введите новое значение баланса (например, <code>1000.50</code>).\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin:give_balance:"))
async def give_balance(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки выдачи баланса"""
    logger.info(f"Обработчик give_balance сработал для пользователя {callback.from_user.id}")
    
    # Получаем ID пользователя из callback_data
    user_id = int(callback.data.split(":")[-1])
    logger.info(f"ID пользователя для выдачи баланса: {user_id}")
    
    # Сохраняем ID пользователя в состоянии
    await state.update_data(user_id=user_id)
    
    # Переходим к состоянию ввода суммы для выдачи
    await state.set_state(BalanceManagement.enter_add_balance)
    logger.info(f"Установлено состояние BalanceManagement.enter_add_balance")
    
    await callback.message.answer(
        "💰 <b>Выдача баланса пользователю</b>\n\n"
        f"Пользователь: <code>{user_id}</code>\n\n"
        "Введите сумму для выдачи (например, <code>500</code>).\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.message(BalanceManagement.enter_new_balance)
async def process_new_balance(message: Message, state: FSMContext, user_repo: UserRepository):
    """Обработка введенного нового баланса"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Изменение баланса отменено", parse_mode=ParseMode.HTML)
        return
    
    try:
        # Получаем новое значение баланса
        new_balance = float(message.text.strip().replace(',', '.'))
        
        # Получаем ID пользователя из состояния
        data = await state.get_data()
        user_id = data.get("user_id")
        
        if not user_id:
            await message.answer("❌ Ошибка: не найден ID пользователя", parse_mode=ParseMode.HTML)
            await state.clear()
            return
        
        # Получаем пользователя
        user = await user_repo.get_user(user_id)
        
        if not user:
            await message.answer(
                "❌ <b>Пользователь не найден</b>\n\n"
                f"Пользователь с ID <code>{user_id}</code> не найден в базе данных.",
                parse_mode=ParseMode.HTML
            )
            await state.clear()
            return
        
        # Сохраняем старый баланс для лога
        old_balance = user.balance
        
        # Обновляем баланс
        user.balance = new_balance
        await user_repo.update_user(user)
        
        # Отправляем сообщение об успешном изменении
        await message.answer(
            "✅ <b>Баланс успешно изменен</b>\n\n"
            f"Пользователь: <code>{user_id}</code>\n"
            f"Старый баланс: <b>{old_balance:.2f}₽</b>\n"
            f"Новый баланс: <b>{new_balance:.2f}₽</b>",
            parse_mode=ParseMode.HTML
        )
        
        # Логируем действие
        logger.info(f"Администратор {message.from_user.id} изменил баланс пользователя {user_id} с {old_balance:.2f}₽ на {new_balance:.2f}₽")
        
        # Очищаем состояние
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат суммы</b>\n\n"
            "Введите число, например <code>1000.50</code>.\n"
            "Для отмены нажмите /cancel",
            parse_mode=ParseMode.HTML
        )


@router.message(BalanceManagement.enter_add_balance)
async def process_add_balance(message: Message, state: FSMContext, user_repo: UserRepository):
    """Обработка введенной суммы для выдачи"""
    logger.info(f"Обработчик process_add_balance сработал для пользователя {message.from_user.id}")
    logger.info(f"Текст сообщения: {message.text}")
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Выдача баланса отменена", parse_mode=ParseMode.HTML)
        return
    
    try:
        # Получаем сумму для выдачи
        add_amount = float(message.text.strip().replace(',', '.'))
        
        if add_amount <= 0:
            await message.answer(
                "❌ <b>Неверная сумма</b>\n\n"
                "Сумма должна быть положительным числом.\n"
                "Для отмены нажмите /cancel",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получаем ID пользователя из состояния
        data = await state.get_data()
        user_id = data.get("user_id")
        
        if not user_id:
            await message.answer("❌ Ошибка: не найден ID пользователя", parse_mode=ParseMode.HTML)
            await state.clear()
            return
        
        # Получаем пользователя
        user = await user_repo.get_user(user_id)
        
        if not user:
            await message.answer(
                "❌ <b>Пользователь не найден</b>\n\n"
                f"Пользователь с ID <code>{user_id}</code> не найден в базе данных.",
                parse_mode=ParseMode.HTML
            )
            await state.clear()
            return
        
        # Сохраняем старый баланс для лога
        old_balance = user.balance
        
        # Обновляем баланс
        user.balance += add_amount
        await user_repo.update_user(user)
        
        # Отправляем сообщение об успешной выдаче
        await message.answer(
            "✅ <b>Баланс успешно выдан</b>\n\n"
            f"Пользователь: <code>{user_id}</code>\n"
            f"Старый баланс: <b>{old_balance:.2f}₽</b>\n"
            f"Выдано: <b>+{add_amount:.2f}₽</b>\n"
            f"Новый баланс: <b>{user.balance:.2f}₽</b>",
            parse_mode=ParseMode.HTML
        )
        
        # Логируем действие
        logger.info(f"Администратор {message.from_user.id} выдал {add_amount:.2f}₽ пользователю {user_id}")
        
        # Очищаем состояние
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат суммы</b>\n\n"
            "Введите число, например <code>500</code>.\n"
            "Для отмены нажмите /cancel",
            parse_mode=ParseMode.HTML
        )


@router.callback_query(F.data == "admin:search_back")
async def back_to_search(callback: CallbackQuery):
    """Возврат к поиску"""
    from app.handlers.search import cmd_search
    await cmd_search(callback.message)
    await callback.answer()