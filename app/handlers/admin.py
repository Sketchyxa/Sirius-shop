from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ParseMode
import asyncio
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
import os
import html

from app.config import Config
from app.keyboards import (
    get_admin_settings_keyboard, 
    get_payment_settings_keyboard,
    get_products_management_keyboard,
    get_search_keyboard
)
from app.services.settings_service import SettingsService
from app.services.crypto_pay_service import CryptoPayService
from app.filters.admin import AdminFilter
from app.states.admin_states import TokenSettings, ProductManagement, UserSearch, Broadcast


router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message, config: Config, settings_service: SettingsService):
    """Обработчик команды настроек (только для администраторов)"""
    # Загружаем актуальные настройки из базы данных
    config.mode.maintenance = await settings_service.get_maintenance_mode()
    config.mode.payments_enabled = await settings_service.get_payments_enabled()
    config.mode.purchases_enabled = await settings_service.get_purchases_enabled()
    
    await message.answer(
        "⚙️ <b>Панель управления</b>\n\n"
        f"🛠 Тех. работы: <b>{'Включены' if config.mode.maintenance else 'Выключены'}</b>\n"
        f"💰 Пополнения: <b>{'Включены' if config.mode.payments_enabled else 'Выключены'}</b>\n"
        f"🛒 Покупки: <b>{'Включены' if config.mode.purchases_enabled else 'Выключены'}</b>\n\n"
        "Используйте кнопки ниже для управления настройками:",
        reply_markup=get_admin_settings_keyboard(
            config.mode.maintenance,
            config.mode.payments_enabled,
            config.mode.purchases_enabled
        ),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "admin:refresh_settings")
async def refresh_settings(callback: CallbackQuery, config: Config, settings_service: SettingsService):
    """Обновление панели настроек"""
    try:
        # Получаем текущие настройки из базы данных
        config.mode.maintenance = await settings_service.get_maintenance_mode()
        config.mode.payments_enabled = await settings_service.get_payments_enabled()
        config.mode.purchases_enabled = await settings_service.get_purchases_enabled()
        
        # Формируем новый текст сообщения
        new_text = (
            "⚙️ <b>Панель управления</b>\n\n"
            f"🛠 Тех. работы: <b>{'Включены' if config.mode.maintenance else 'Выключены'}</b>\n"
            f"💰 Пополнения: <b>{'Включены' if config.mode.payments_enabled else 'Выключены'}</b>\n"
            f"🛒 Покупки: <b>{'Включены' if config.mode.purchases_enabled else 'Выключены'}</b>\n\n"
            "Используйте кнопки ниже для управления настройками:"
        )
        
        # Формируем новую клавиатуру
        new_markup = get_admin_settings_keyboard(
            config.mode.maintenance,
            config.mode.payments_enabled,
            config.mode.purchases_enabled
        )
        
        try:
            # Пробуем обновить сообщение
            await callback.message.edit_text(
                new_text,
                reply_markup=new_markup,
                parse_mode=ParseMode.HTML
            )
            await callback.answer("Настройки обновлены")
        except TelegramBadRequest as e:
            # Если сообщение не изменилось, просто отвечаем без ошибки
            if "message is not modified" in str(e):
                await callback.answer("Настройки уже актуальны")
            else:
                # Если другая ошибка, пробрасываем её дальше
                raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении настроек: {e}")
        await callback.answer("Произошла ошибка при обновлении настроек", show_alert=True)


@router.callback_query(F.data == "admin:toggle_maintenance")
async def toggle_maintenance(callback: CallbackQuery, config: Config, settings_service: SettingsService):
    """Переключение режима технических работ"""
    new_value = not config.mode.maintenance
    await settings_service.set_maintenance_mode(new_value)
    config.mode.maintenance = new_value
    
    status = "включен" if new_value else "выключен"
    await callback.answer(f"Режим тех. работ {status}")
    
    await refresh_settings(callback, config, settings_service)


@router.callback_query(F.data == "admin:toggle_payments")
async def toggle_payments(callback: CallbackQuery, config: Config, settings_service: SettingsService):
    """Переключение возможности пополнений"""
    new_value = not config.mode.payments_enabled
    await settings_service.set_payments_enabled(new_value)
    config.mode.payments_enabled = new_value
    
    status = "включены" if new_value else "выключены"
    await callback.answer(f"Пополнения {status}")
    
    await refresh_settings(callback, config, settings_service)


@router.callback_query(F.data == "admin:toggle_purchases")
async def toggle_purchases(callback: CallbackQuery, config: Config, settings_service: SettingsService):
    """Переключение возможности покупок"""
    new_value = not config.mode.purchases_enabled
    await settings_service.set_purchases_enabled(new_value)
    config.mode.purchases_enabled = new_value
    
    status = "включены" if new_value else "выключены"
    await callback.answer(f"Покупки {status}")
    
    await refresh_settings(callback, config, settings_service)


@router.callback_query(F.data == "admin:logs")
async def show_logs(callback: CallbackQuery):
    """Показать последние логи бота"""
    try:
        # Проверяем наличие файлов логов
        log_files = {
            "errors.log": "Логи ошибок",
            "info.log": "Информационные логи",
            "bot.log": "Полные логи"
        }
        
        available_logs = []
        for file_name, description in log_files.items():
            log_path = os.path.join("logs", file_name)
            if os.path.exists(log_path):
                available_logs.append((log_path, description))
        
        if not available_logs:
            await callback.answer("Файлы логов не найдены", show_alert=True)
            return
        
        # Берем последний файл из списка (приоритет: errors.log, info.log, bot.log)
        log_path, description = available_logs[0]
        
        with open(log_path, "r", encoding="utf-8") as f:
            logs = f.readlines()[-15:]  # Последние 15 строк логов
        
        # Экранируем специальные символы HTML
        escaped_logs = [html.escape(line) for line in logs]
        
        log_text = f"📊 <b>{description}:</b>\n\n"
        log_text += "<pre>" + "".join(escaped_logs) + "</pre>"
        
        # Ограничиваем длину сообщения
        if len(log_text) > 4000:
            log_text = log_text[:3990] + "...</pre>"
        
        await callback.answer("Загружаю логи")
        await callback.message.answer(log_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка при чтении логов: {e}")
        await callback.answer("Ошибка при чтении логов", show_alert=True)


@router.callback_query(F.data == "admin:back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.answer("Возврат в главное меню")
    await callback.message.delete()


# Настройки платежных систем

@router.callback_query(F.data == "admin:payment_settings")
async def payment_settings(callback: CallbackQuery, config: Config, settings_service: SettingsService):
    """Настройки платежных систем"""
    crypto_pay_token = await settings_service.get_crypto_pay_token()
    crypto_pay_testnet = await settings_service.get_crypto_pay_testnet()
    config.payment.crypto_pay_testnet = crypto_pay_testnet
    
    crypto_pay_status = "✅ Настроен" if crypto_pay_token else "❌ Не настроен"
    
    await callback.message.edit_text(
        "💰 <b>Настройки платежных систем</b>\n\n"
        f"🪙 Crypto Pay: <b>{crypto_pay_status}</b>\n"
        f"🧪 Режим: <b>{'Тестовый' if config.payment.crypto_pay_testnet else 'Боевой'}</b>\n\n"
        "Используйте кнопки ниже для настройки платежных систем:",
        reply_markup=get_payment_settings_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.callback_query(F.data == "admin:delete_crypto_pay_token")
async def delete_crypto_pay_token(callback: CallbackQuery, settings_service: SettingsService):
    """Удаление токена Crypto Pay (вместо переключателя тест/боевой)"""
    await settings_service.set_crypto_pay_token("")
    await callback.answer("Токен удален")
    # Обновляем экран настроек
    config = callback.bot['config'] if 'config' in callback.bot else None
    from app.services.settings_service import SettingsService as _S
    ss = _S()
    if config:
        await payment_settings(callback, config, ss)


@router.callback_query(F.data == "admin:back_to_settings")
async def back_to_settings(callback: CallbackQuery, config: Config, settings_service: SettingsService):
    """Возврат в настройки бота"""
    await refresh_settings(callback, config, settings_service)
    await callback.answer()


@router.callback_query(F.data == "admin:setup_crypto_pay")
async def setup_crypto_pay(callback: CallbackQuery, state: FSMContext):
    """Настройка токена Crypto Pay"""
    await state.set_state(TokenSettings.enter_crypto_pay_token)
    
    await callback.message.edit_text(
        "🪙 <b>Настройка Crypto Pay</b>\n\n"
        "Для настройки Crypto Pay вам необходимо:\n"
        "1. Открыть @CryptoBot (или @CryptoTestnetBot для тестовой сети)\n"
        "2. Перейти в раздел <b>Crypto Pay</b>\n"
        "3. Нажать <b>Create App</b>\n"
        "4. Ввести название приложения и получить токен\n\n"
        "<b>Отправьте полученный токен в следующем сообщении</b>\n\n"
        "Для отмены нажмите /cancel",
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.message(TokenSettings.enter_crypto_pay_token)
async def process_crypto_pay_token(message: Message, state: FSMContext, config: Config, settings_service: SettingsService):
    """Обработка введенного токена Crypto Pay"""
    token = message.text.strip()
    
    if token == "/cancel":
        await state.clear()
        await message.answer("❌ Настройка Crypto Pay отменена", parse_mode=ParseMode.HTML)
        return
    
    # Проверяем формат токена (примерно)
    if not token or ":" not in token:
        await message.answer(
            "❌ <b>Неверный формат токена</b>\n\n"
            "Токен должен иметь формат вида: <code>12345:AABBCCDDEEFFaabbccddeeff</code>\n\n"
            "Попробуйте еще раз или нажмите /cancel для отмены",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Сразу сохраняем токен
    await settings_service.set_crypto_pay_token(token)
    config.payment.crypto_pay_token = token
    
    # Отправляем сообщение о сохранении
    await message.answer("✅ <b>Токен Crypto Pay сохранен</b>", parse_mode=ParseMode.HTML)
    
    # Проверяем работоспособность токена
    try:
        # Создаем сервис для проверки токена
        crypto_pay = CryptoPayService(
            api_token=token,
            testnet=config.payment.crypto_pay_testnet
        )
        
        # Пробуем выполнить тестовый запрос
        app_info = await crypto_pay.get_me()
        
        # Если запрос успешен, показываем информацию о приложении
        await message.answer(
            "✅ <b>Токен Crypto Pay работает корректно</b>\n\n"
            f"Информация о приложении:\n"
            f"- ID: <code>{app_info.get('app_id')}</code>\n"
            f"- Название: <b>{app_info.get('name')}</b>\n"
            f"- Платформа: <b>{app_info.get('payment_processing_bot_username', '@CryptoBot')}</b>\n\n"
            f"Режим: <b>{'Тестовый' if config.payment.crypto_pay_testnet else 'Боевой'}</b>\n\n"
            "Теперь вы можете использовать Crypto Pay для приема платежей.",
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"Успешная проверка токена Crypto Pay: {app_info.get('name')}")
        
    except Exception as e:
        logger.error(f"Ошибка при проверке токена Crypto Pay: {e}")
        
        # Показываем ошибку
        await message.answer(
            "❌ <b>Токен сохранен, но при проверке возникла ошибка</b>\n\n"
            f"Ошибка: <code>{html.escape(str(e))}</code>\n\n"
            "Возможные причины:\n"
            "- Неверный формат токена\n"
            "- Токен отозван или недействителен\n"
            "- Проблемы с подключением к API\n"
            "- Несоответствие режима (тестовый/боевой)\n\n"
            "Попробуйте переключить режим (тестовый/боевой) в настройках платежей.",
            parse_mode=ParseMode.HTML
        )
    
    # Очищаем состояние
    await state.clear()


@router.callback_query(F.data == "admin:check_crypto_pay")
async def check_crypto_pay(callback: CallbackQuery, config: Config, settings_service: SettingsService):
    """Проверка работы Crypto Pay"""
    token = await settings_service.get_crypto_pay_token()
    crypto_pay_testnet = await settings_service.get_crypto_pay_testnet()
    config.payment.crypto_pay_testnet = crypto_pay_testnet
    
    if not token:
        await callback.answer("❌ Токен Crypto Pay не настроен", show_alert=True)
        return
    
    try:
        # Создаем сервис для проверки токена
        crypto_pay = CryptoPayService(
            api_token=token,
            testnet=config.payment.crypto_pay_testnet
        )
        
        # Проверяем токен с помощью метода getMe
        app_info = await crypto_pay.get_me()
        
        # Если запрос успешен, показываем информацию о приложении
        await callback.message.edit_text(
            "✅ <b>Токен Crypto Pay работает корректно</b>\n\n"
            f"Информация о приложении:\n"
            f"- ID: <code>{app_info.get('app_id')}</code>\n"
            f"- Название: <b>{app_info.get('name')}</b>\n"
            f"- Платформа: <b>{app_info.get('payment_processing_bot_username', '@CryptoBot')}</b>\n\n"
            f"Режим: <b>{'Тестовый' if config.payment.crypto_pay_testnet else 'Боевой'}</b>",
            reply_markup=get_payment_settings_keyboard(),
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"Успешная проверка токена Crypto Pay: {app_info.get('name')}")
        
    except Exception as e:
        logger.error(f"Ошибка при проверке токена Crypto Pay: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка при проверке токена Crypto Pay</b>\n\n"
            f"Ошибка: <code>{html.escape(str(e))}</code>\n\n"
            "Возможные причины:\n"
            "- Неверный формат токена\n"
            "- Токен отозван или недействителен\n"
            "- Проблемы с подключением к API\n"
            "- Несоответствие режима (тестовый/боевой)\n\n"
            "Попробуйте настроить токен заново или изменить режим (тестовый/боевой).",
            reply_markup=get_payment_settings_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()