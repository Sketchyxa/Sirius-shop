import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from loguru import logger

from app.config import Config
from app.database.repositories import UserRepository
from app.services.crypto_pay_service import CryptoPayService
from app.services.settings_service import SettingsService


router = Router()


# Клавиатура с суммами пополнения
def get_deposit_amounts_keyboard() -> InlineKeyboardBuilder:
    """Создает клавиатуру с суммами пополнения"""
    kb = InlineKeyboardBuilder()
    
    # Стандартные суммы пополнения
    amounts = [100, 250, 500, 1000, 2500, 5000]
    
    for amount in amounts:
        kb.add(InlineKeyboardButton(
            text=f"{amount} ₽",
            callback_data=f"deposit:{amount}"
        ))
    
    # Кнопка отмены
    kb.add(InlineKeyboardButton(
        text="🔙 Отмена",
        callback_data="deposit:cancel"
    ))
    
    kb.adjust(3)  # По 3 кнопки в ряду
    
    return kb


@router.message(Command("deposit"))
@router.message(F.text.lower().in_(["пополнить", "пополнить баланс", "💰 пополнить"]))
async def cmd_deposit(message: Message, config: Config, settings_service: SettingsService):
    """Обработчик команды пополнения баланса"""
    # Проверяем, включены ли пополнения
    if not config.mode.payments_enabled:
        await message.answer("❌ <b>Пополнения временно отключены</b>\n\nПопробуйте позже.", parse_mode=ParseMode.HTML)
        return
    
    # Проверяем, настроен ли токен Crypto Pay
    crypto_pay_token = await settings_service.get_crypto_pay_token()
    if not crypto_pay_token:
        await message.answer("❌ <b>Система пополнения временно недоступна</b>\n\nПопробуйте позже.", parse_mode=ParseMode.HTML)
        return
    
    await message.answer(
        "💰 <b>Пополнение баланса</b>\n\n"
        "Выберите сумму пополнения или введите свою сумму в рублях:",
        reply_markup=get_deposit_amounts_keyboard().as_markup(),
        parse_mode=ParseMode.HTML
    )


@router.message(lambda message: False)
async def process_custom_amount(message: Message, config: Config, settings_service: SettingsService, user_repo: UserRepository, state: FSMContext):
    """Обработка произвольной суммы пополнения"""
    # Проверяем, не находимся ли мы в состоянии добавления товара
    current_state = await state.get_state()
    if current_state and "ProductManagement" in current_state:
        # Если мы в состоянии добавления товара, игнорируем это сообщение
        return
    
    # Проверяем, не находимся ли мы в состоянии выдачи баланса
    if current_state and "BalanceManagement" in current_state:
        # Если мы в состоянии выдачи баланса, игнорируем это сообщение
        logger.info(f"Игнорируем числовое сообщение в состоянии BalanceManagement: {message.text}")
        return
    
    # Проверяем, включены ли пополнения
    if not config.mode.payments_enabled:
        await message.answer("❌ <b>Пополнения временно отключены</b>\n\nПопробуйте позже.", parse_mode=ParseMode.HTML)
        return
    
    try:
        # Преобразуем строку в число
        amount = float(message.text.replace(',', '.'))
        
        # Проверяем минимальную сумму
        if amount < 10:
            await message.answer("❌ <b>Минимальная сумма пополнения - 10 ₽</b>", parse_mode=ParseMode.HTML)
            return
        
        # Проверяем максимальную сумму
        if amount > 100000:
            await message.answer("❌ <b>Максимальная сумма пополнения - 100,000 ₽</b>", parse_mode=ParseMode.HTML)
            return
        
        # Получаем токен Crypto Pay
        crypto_pay_token = await settings_service.get_crypto_pay_token()
        crypto_pay_testnet = await settings_service.get_crypto_pay_testnet()
        
        # Создаем сервис Crypto Pay
        crypto_pay = CryptoPayService(
            api_token=crypto_pay_token,
            testnet=crypto_pay_testnet
        )
        
        # Создаем уникальный идентификатор для платежа
        payment_id = str(uuid.uuid4())
        
        # Получаем курс обмена для USDT
        try:
            exchange_rates = await crypto_pay.get_exchange_rates()
            usdt_rate = 1.0  # По умолчанию 1:1
            
            # Ищем курс USDT к RUB
            for rate in exchange_rates:
                if rate.get("source") == "USDT" and rate.get("target") == "RUB":
                    usdt_rate = float(rate.get("rate", 1.0))
                    break
            
            # Конвертируем сумму в USDT
            usdt_amount = amount / usdt_rate
            
            # Округляем до 2 знаков после запятой
            usdt_amount = round(usdt_amount, 2)
            
            # Создаем счет на оплату
            invoice = await crypto_pay.create_invoice(
                amount=usdt_amount,
                asset="USDT",  # Используем USDT как основную валюту
                description=f"Пополнение баланса на {amount} ₽",
                hidden_message="Спасибо за пополнение баланса!",
                payload=f"{payment_id}:{message.from_user.id}:{amount}",
                allow_comments=True,
                allow_anonymous=False,
                expires_in=60 * 30  # 30 минут на оплату
            )
            
            # Создаем клавиатуру для проверки оплаты
            kb = InlineKeyboardBuilder()
            kb.add(InlineKeyboardButton(
                text="💳 Оплатить",
                url=invoice["bot_invoice_url"]
            ))
            kb.add(InlineKeyboardButton(
                text="🔄 Проверить оплату",
                callback_data=f"check_payment:{invoice['invoice_id']}"
            ))
            kb.add(InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="cancel_payment"
            ))
            
            # Отправляем сообщение с информацией о платеже
            await message.answer(
                f"💰 <b>Пополнение баланса</b>\n\n"
                f"Сумма: <b>{amount} ₽</b>\n"
                f"К оплате: <b>{usdt_amount} USDT</b>\n\n"
                f"Для оплаты нажмите кнопку ниже и следуйте инструкциям.\n"
                f"После оплаты нажмите 'Проверить оплату'.",
                reply_markup=kb.as_markup(),
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Создан счет на пополнение: {invoice['invoice_id']} для пользователя {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при создании платежа: {e}")
            await message.answer("❌ <b>Ошибка при создании платежа</b>\n\nПопробуйте позже.", parse_mode=ParseMode.HTML)
            
    except ValueError:
        await message.answer("❌ <b>Неверный формат суммы</b>\n\nВведите число, например: 100 или 100.50", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Ошибка при обработке суммы: {e}")
        await message.answer("❌ <b>Произошла ошибка</b>\n\nПопробуйте позже.", parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("deposit:"))
async def process_deposit_amount(callback: CallbackQuery, config: Config, settings_service: SettingsService, user_repo: UserRepository):
    """Обработка выбранной суммы пополнения"""
    # Получаем сумму из callback_data
    amount_str = callback.data.split(":")[1]
    
    # Проверяем на отмену
    if amount_str == "cancel":
        await callback.message.edit_text("❌ <b>Пополнение отменено</b>", parse_mode=ParseMode.HTML)
        await callback.answer()
        return
    
    try:
        # Преобразуем строку в число
        amount = float(amount_str)
        
        # Проверяем минимальную сумму
        if amount < 10:
            await callback.answer("Минимальная сумма пополнения - 10 ₽", show_alert=True)
            return
        
        # Получаем токен Crypto Pay
        crypto_pay_token = await settings_service.get_crypto_pay_token()
        crypto_pay_testnet = await settings_service.get_crypto_pay_testnet()
        
        # Создаем сервис Crypto Pay
        crypto_pay = CryptoPayService(
            api_token=crypto_pay_token,
            testnet=crypto_pay_testnet
        )
        
        # Создаем уникальный идентификатор для платежа
        payment_id = str(uuid.uuid4())
        
        # Получаем курс обмена для USDT
        exchange_rates = await crypto_pay.get_exchange_rates()
        usdt_rate = 1.0  # По умолчанию 1:1
        
        # Ищем курс USDT к RUB
        for rate in exchange_rates:
            if rate.get("source") == "USDT" and rate.get("target") == "RUB":
                usdt_rate = float(rate.get("rate", 1.0))
                break
        
        # Конвертируем сумму в USDT
        usdt_amount = amount / usdt_rate
        
        # Округляем до 2 знаков после запятой
        usdt_amount = round(usdt_amount, 2)
        
        # Создаем счет на оплату
        invoice = await crypto_pay.create_invoice(
            amount=usdt_amount,
            asset="USDT",  # Используем USDT как основную валюту
            description=f"Пополнение баланса на {amount} ₽",
            hidden_message="Спасибо за пополнение баланса!",
            payload=f"{payment_id}:{callback.from_user.id}:{amount}",
            allow_comments=True,
            allow_anonymous=False,
            expires_in=60 * 30  # 30 минут на оплату
        )
        
        # Создаем клавиатуру для проверки оплаты
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(
            text="💳 Оплатить",
            url=invoice["bot_invoice_url"]
        ))
        kb.add(InlineKeyboardButton(
            text="🔄 Проверить оплату",
            callback_data=f"check_payment:{invoice['invoice_id']}"
        ))
        kb.add(InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="cancel_payment"
        ))
        
        # Отправляем сообщение с информацией о платеже
        await callback.message.edit_text(
            f"💰 <b>Пополнение баланса</b>\n\n"
            f"Сумма: <b>{amount} ₽</b>\n"
            f"К оплате: <b>{usdt_amount} USDT</b>\n\n"
            f"Для оплаты нажмите кнопку ниже и следуйте инструкциям.\n"
            f"После оплаты нажмите 'Проверить оплату'.",
            reply_markup=kb.as_markup(),
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"Создан счет на пополнение: {invoice['invoice_id']} для пользователя {callback.from_user.id}")
        
    except ValueError:
        await callback.answer("Некорректная сумма", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при создании счета: {e}")
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка при создании счета</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment_status(callback: CallbackQuery, config: Config, settings_service: SettingsService, user_repo: UserRepository):
    """Проверка статуса оплаты"""
    invoice_id = callback.data.split(":")[1]
    
    try:
        # Получаем токен Crypto Pay
        crypto_pay_token = await settings_service.get_crypto_pay_token()
        crypto_pay_testnet = await settings_service.get_crypto_pay_testnet()
        
        # Создаем сервис Crypto Pay
        crypto_pay = CryptoPayService(
            api_token=crypto_pay_token,
            testnet=crypto_pay_testnet
        )
        
        # Получаем информацию о счете
        invoices = await crypto_pay.get_invoices(invoice_ids=[invoice_id])
        
        if not invoices.get("items"):
            await callback.answer("❌ Счет не найден", show_alert=True)
            return
        
        invoice = invoices["items"][0]
        
        # Проверяем статус счета
        if invoice["status"] == "paid":
            # Счет оплачен, пополняем баланс
            payload_parts = invoice.get("payload", "").split(":")
            if len(payload_parts) != 3:
                logger.error(f"Неверный формат payload: {invoice.get('payload')}")
                await callback.answer("❌ Ошибка при обработке платежа", show_alert=True)
                return
            
            _, user_id, amount = payload_parts
            user_id = int(user_id)
            amount = float(amount)
            
            # Получаем пользователя
            user = await user_repo.get_user(user_id)
            if not user:
                logger.error(f"Пользователь не найден: {user_id}")
                await callback.answer("❌ Пользователь не найден", show_alert=True)
                return
            
            # Пополняем баланс
            user.balance += amount
            await user_repo.update_user(user)
            
            # Отправляем сообщение об успешном пополнении
            await callback.message.edit_text(
                f"✅ <b>Баланс успешно пополнен!</b>\n\n"
                f"Сумма: <b>{amount} ₽</b>\n"
                f"Текущий баланс: <b>{user.balance} ₽</b>\n\n"
                f"Спасибо за пополнение!",
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Успешное пополнение баланса на {amount} ₽ для пользователя {user_id}")
            
        elif invoice["status"] == "active":
            # Счет еще активен, ожидаем оплату
            await callback.answer("Счет еще не оплачен. Пожалуйста, оплатите счет.", show_alert=True)
        else:
            # Счет истек или отменен
            await callback.message.edit_text(
                "❌ <b>Счет истек или был отменен</b>\n\n"
                "Пожалуйста, создайте новый запрос на пополнение.",
                parse_mode=ParseMode.HTML
            )
    
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса оплаты: {e}")
        await callback.answer("❌ Произошла ошибка при проверке статуса оплаты", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery):
    """Отмена платежа"""
    await callback.message.edit_text("❌ <b>Пополнение отменено</b>", parse_mode=ParseMode.HTML)
    await callback.answer()