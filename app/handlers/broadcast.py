from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from loguru import logger

from app.filters.admin import AdminFilter
from app.states.admin_states import Broadcast
from app.keyboards import get_broadcast_keyboard
from app.database.repositories import UserRepository


router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """Обработчик команды рассылки (только для администраторов)"""
    await state.set_state(Broadcast.enter_message)
    
    await message.answer(
        "📨 <b>Создание рассылки</b>\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям.\n"
        "Поддерживается HTML-разметка.\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )


@router.message(Broadcast.enter_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обработка сообщения для рассылки"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Рассылка отменена")
        return
    
    # Очищаем текст от неподдерживаемых HTML-тегов и исправляем незакрытые теги
    import re
    clean_text = message.text
    
    # Удаляем неподдерживаемые теги
    clean_text = re.sub(r'<p[^>]*>', '', clean_text)
    clean_text = re.sub(r'</p>', '\n', clean_text)
    clean_text = re.sub(r'<br[^>]*>', '\n', clean_text)
    clean_text = re.sub(r'<div[^>]*>', '', clean_text)
    clean_text = re.sub(r'</div>', '\n', clean_text)
    
    # Исправляем незакрытые теги
    # Подсчитываем количество открытых и закрытых тегов
    open_b_tags = len(re.findall(r'<b[^>]*>', clean_text))
    close_b_tags = len(re.findall(r'</b>', clean_text))
    
    # Если есть незакрытые теги <b>, добавляем их в конец
    if open_b_tags > close_b_tags:
        missing_tags = open_b_tags - close_b_tags
        clean_text += '</b>' * missing_tags
    
    # Аналогично для других тегов
    open_i_tags = len(re.findall(r'<i[^>]*>', clean_text))
    close_i_tags = len(re.findall(r'</i>', clean_text))
    if open_i_tags > close_i_tags:
        missing_tags = open_i_tags - close_i_tags
        clean_text += '</i>' * missing_tags
    
    open_u_tags = len(re.findall(r'<u[^>]*>', clean_text))
    close_u_tags = len(re.findall(r'</u>', clean_text))
    if open_u_tags > close_u_tags:
        missing_tags = open_u_tags - close_u_tags
        clean_text += '</u>' * missing_tags
    
    open_s_tags = len(re.findall(r'<s[^>]*>', clean_text))
    close_s_tags = len(re.findall(r'</s>', clean_text))
    if open_s_tags > close_s_tags:
        missing_tags = open_s_tags - close_s_tags
        clean_text += '</s>' * missing_tags
    
    # Сохраняем очищенный текст сообщения
    await state.update_data(broadcast_text=clean_text)
    
    # Запрашиваем подтверждение
    await state.set_state(Broadcast.confirm_broadcast)
    
    await message.answer(
        "📨 <b>Подтверждение рассылки</b>\n\n"
        "Вот как будет выглядеть ваше сообщение:\n\n"
        f"{clean_text}\n\n"
        "Вы уверены, что хотите отправить это сообщение всем пользователям?",
        reply_markup=get_broadcast_keyboard(),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(Broadcast.confirm_broadcast, F.data == "admin:broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, user_repo: UserRepository):
    """Подтверждение и отправка рассылки"""
    await callback.answer("Рассылка начата")
    
    # Получаем текст рассылки
    data = await state.get_data()
    broadcast_text = data.get("broadcast_text")
    
    # Получаем всех пользователей
    users = await user_repo.get_all_users(limit=1000)
    
    # Счетчики для статистики
    total_users = len(users)
    successful = 0
    failed = 0
    
    # Отправляем сообщение о начале рассылки
    await callback.message.edit_text(
        "📨 <b>Рассылка начата</b>\n\n"
        f"Всего пользователей: {total_users}\n"
        "Пожалуйста, подождите...",
        parse_mode=ParseMode.HTML
    )
    
    # Отправляем сообщения пользователям
    for user in users:
        try:
            from aiogram import Bot
            bot = callback.bot
            
            # Отправляем сообщение пользователю
            await bot.send_message(
                chat_id=user.user_id,
                text=broadcast_text,
                parse_mode=ParseMode.HTML
            )
            successful += 1
            
            # Обновляем статус каждые 10 отправленных сообщений
            if successful % 10 == 0:
                try:
                    await callback.message.edit_text(
                        "📨 <b>Рассылка в процессе</b>\n\n"
                        f"Всего пользователей: {total_users}\n"
                        f"Отправлено: {successful}\n"
                        f"Ошибок: {failed}\n\n"
                        "Пожалуйста, подождите...",
                        parse_mode=ParseMode.HTML
                    )
                except Exception:
                    pass
                
        except Exception as e:
            logger.error(f"Ошибка при отправке рассылки пользователю {user.user_id}: {e}")
            failed += 1
    
    # Отправляем итоговую статистику
    await callback.message.edit_text(
        "📨 <b>Рассылка завершена</b>\n\n"
        f"Всего пользователей: {total_users}\n"
        f"Успешно отправлено: {successful}\n"
        f"Ошибок: {failed}",
        parse_mode=ParseMode.HTML
    )
    
    # Очищаем состояние
    await state.clear()


@router.callback_query(Broadcast.confirm_broadcast, F.data == "admin:broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await callback.answer("Рассылка отменена")
    await callback.message.edit_text("❌ <b>Рассылка отменена</b>", parse_mode=ParseMode.HTML)
    await state.clear()
    
    # Возвращаемся в админ-панель
    from app.handlers.admin_panel import cmd_admin_panel
    await cmd_admin_panel(callback.message)