from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from loguru import logger

from app.filters.admin import AdminFilter
from app.keyboards import get_main_keyboard, get_payment_settings_keyboard


router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(Command("admin"))
@router.message(F.text == "🛠 Админ-панель")
async def cmd_admin_panel(message: Message):
    """Обработчик команды админ-панели (только для администраторов)"""
    # Создаем клавиатуру админ-панели
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="📨 Рассылка")],
            [KeyboardButton(text="📦 Управление товарами")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "🛠 <b>Админ-панель</b>\n\n"
        "Выберите нужный раздел:",
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )


@router.message(F.text == "🔙 Назад")
async def cmd_back_to_main(message: Message):
    """Возврат в главное меню"""
    await message.answer(
        "✅ Возврат в главное меню",
        reply_markup=get_main_keyboard(is_admin=True)
    )





@router.message(F.text == "📦 Управление товарами")
async def cmd_products_management(message: Message):
    """Обработчик команды управления товарами"""
    from app.keyboards import get_products_management_keyboard
    
    await message.answer(
        "📦 <b>Управление товарами</b>\n\n"
        "Выберите действие:",
        reply_markup=get_products_management_keyboard(),
        parse_mode=ParseMode.HTML
    )


@router.message(F.text == "🔍 Поиск")
async def cmd_search(message: Message):
    """Обработчик команды поиска"""
    from app.keyboards import get_search_keyboard
    
    await message.answer(
        "🔍 <b>Поиск пользователя или чека</b>\n\n"
        "Выберите тип поиска:",
        reply_markup=get_search_keyboard(),
        parse_mode=ParseMode.HTML
    )


@router.message(F.text == "📨 Рассылка")
async def cmd_broadcast(message: Message, state: FSMContext):
    """Обработчик команды рассылки"""
    from app.states.admin_states import Broadcast
    
    await state.set_state(Broadcast.enter_message)
    
    await message.answer(
        "📨 <b>Создание рассылки</b>\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям.\n"
        "Поддерживается HTML-разметка.\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )





@router.message(F.text == "🔙 Назад к админ-панели")
async def cmd_back_to_admin_panel(message: Message):
    """Возврат в админ-панель"""
    await cmd_admin_panel(message)