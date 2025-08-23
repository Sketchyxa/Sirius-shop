from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from loguru import logger
import uuid

from app.database.repositories import UserRepository, ProductRepository, TransactionRepository, ProductItemRepository
from app.database.models import Transaction
from app.keyboards import (
    get_products_keyboard,
    get_product_actions_keyboard,
    get_payment_method_keyboard,
    get_confirm_purchase_keyboard,
    get_user_product_actions_keyboard,
)
from app.states.user_states import BuyProduct
from app.services.crypto_pay_service import CryptoPayService
from app.services.settings_service import SettingsService
from app.config import Config
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import LabeledPrice, PreCheckoutQuery


router = Router()


@router.message(Command("buy"))
@router.message(F.text == "🛒 Купить")
async def cmd_buy(message: Message, product_repo: ProductRepository, config: Config):
    """Обработчик команды покупки"""
    logger.info(f"Пользователь {message.from_user.id} нажал кнопку покупки")
    
    # Проверяем, включены ли покупки
    if not config.mode.purchases_enabled:
        await message.answer("❌ <b>Покупки временно отключены</b>\n\nПопробуйте позже или обратитесь к администратору.", parse_mode=ParseMode.HTML)
        return
    
    try:
        products = await product_repo.get_all_products(available_only=True)
        logger.info(f"Найдено товаров: {len(products)}")
        
        if not products:
            await message.answer("❌ У вас ничего не куплено.", parse_mode=ParseMode.HTML)
            return
        
        keyboard = get_products_keyboard(products)
        logger.info(f"Клавиатура создана: {keyboard}")
        
        await message.answer(
            "🛒 <b>Выберите товар для покупки:</b>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        logger.info("Сообщение отправлено успешно")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике покупки: {e}")
        await message.answer("❌ Произошла ошибка при загрузке товаров. Попробуйте позже.", parse_mode=ParseMode.HTML)





@router.callback_query(F.data.startswith("product:"))
async def show_product(callback: CallbackQuery, product_repo: ProductRepository):
    """Показ информации о товаре"""
    product_id = callback.data.split(":")[1]
    product = await product_repo.get_product(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    # Очищаем описание от некорректных HTML-тегов
    import re
    clean_description = product.description or 'Описание отсутствует'
    if clean_description != 'Описание отсутствует':
        # Удаляем все HTML-теги
        clean_description = re.sub(r'<[^>]+>', '', clean_description)
        # Экранируем специальные символы
        clean_description = clean_description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Формируем текст с информацией о товаре
    text = (
        f"📦 {product.name}\n\n"
        f"{clean_description}\n\n"
        f"💰 Цена: {product.price:.2f}₽\n"
        f"🔢 В наличии: {product.quantity} шт."
    )
    
    # Если у товара есть изображение, отправляем его
    if product.image_url:
        try:
            await callback.message.answer_photo(
                photo=product.image_url,
                caption=text,
                reply_markup=get_user_product_actions_keyboard(str(product.id), bool(product.stars_enabled and product.stars_price)),
                parse_mode=ParseMode.HTML
            )
            await callback.message.delete()
        except TelegramBadRequest as e:
            # Некорректный file_id/URL — показываем карточку без фото, чтобы не падать
            logger.error(
                f"Ошибка отправки фото товара {product.id}: {e}. image_url={product.image_url}"
            )
            try:
                await callback.message.edit_text(
                    text=text,
                    reply_markup=get_user_product_actions_keyboard(str(product.id), bool(product.stars_enabled and product.stars_price)),
                    parse_mode=ParseMode.HTML
                )
            except TelegramBadRequest:
                await callback.message.answer(
                    text,
                    reply_markup=get_user_product_actions_keyboard(str(product.id), bool(product.stars_enabled and product.stars_price)),
                    parse_mode=ParseMode.HTML
                )
    else:
        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=get_user_product_actions_keyboard(str(product.id), bool(product.stars_enabled and product.stars_price)),
                parse_mode=ParseMode.HTML
            )
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось отредактировать сообщение в show_product: {e}")
            await callback.message.answer(
                text=text,
                reply_markup=get_user_product_actions_keyboard(str(product.id), bool(product.stars_enabled and product.stars_price)),
                parse_mode=ParseMode.HTML
            )
            try:
                await callback.message.delete()
            except TelegramBadRequest:
                pass
    
    await callback.answer()


@router.callback_query(F.data.startswith("buy_stars:"))
async def start_purchase_stars(callback: CallbackQuery, product_repo: ProductRepository, user_repo: UserRepository):
    """Начало покупки за Звезды Telegram (UI-часть). Фактическую оплату инициирует клиент через Bot API Stars UI."""
    product_id = callback.data.split(":")[1]
    product = await product_repo.get_product(product_id)
    if not product or not (product.stars_enabled and product.stars_price):
        await callback.answer("Оплата звездами недоступна", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            f"✨ <b>Покупка за звезды</b>\n\n"
            f"📦 Товар: <b>{product.name}</b>\n"
            f"✨ Стоимость: <b>{int(product.stars_price)} ⭐</b>\n\n"
            f"Нажмите кнопку 'Купить за звезды' ниже, чтобы продолжить в интерфейсе Telegram.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✨ Купить за звезды", callback_data=f"buy_stars_confirm:{product.id}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"product:{product.id}")]
            ]),
            parse_mode=ParseMode.HTML
        )
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отредактировать сообщение в start_purchase_stars: {e}")
        await callback.message.answer(
            f"✨ <b>Покупка за звезды</b>\n\n"
            f"📦 Товар: <b>{product.name}</b>\n"
            f"✨ Стоимость: <b>{int(product.stars_price)} ⭐</b>\n\n"
            f"Нажмите кнопку 'Купить за звезды' ниже, чтобы продолжить в интерфейсе Telegram.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✨ Купить за звезды", callback_data=f"buy_stars_confirm:{product.id}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"product:{product.id}")]
            ]),
            parse_mode=ParseMode.HTML
        )
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("buy_stars_confirm:"))
async def create_stars_invoice(
    callback: CallbackQuery,
    product_repo: ProductRepository,
    transaction_repo: TransactionRepository,
):
    """Создаем инвойс оплаты звездами (Bot API, currency=XTR)."""
    product_id = callback.data.split(":")[1]
    product = await product_repo.get_product(product_id)
    if not product or not (product.stars_enabled and product.stars_price):
        await callback.answer("Оплата звездами недоступна", show_alert=True)
        return
    # Создаем транзакцию pending (идемпотентность по существующей незавершенной транзакции)
    from uuid import uuid4
    receipt_id = f"{uuid4().hex[:16]}"
    transaction = await transaction_repo.create_transaction(
        user_id=callback.from_user.id,
        amount=product.price,
        transaction_type="purchase",
        status="pending",
        payment_method="stars",
        product_id=product_id,
        receipt_id=receipt_id,
    )
    payload = f"stars:{product_id}:{transaction.id}"
    title = product.name[:32]
    # Очищаем описание как в show_product
    import re
    clean_description = product.description or "Описание отсутствует"
    if clean_description != "Описание отсутствует":
        clean_description = re.sub(r"<[^>]+>", "", clean_description)
    try:
        await callback.message.answer_invoice(
            title=title or "Товар",
            description=clean_description[:255],
            payload=payload,
            provider_token="",  # для XTR провайдер не требуется
            currency="XTR",
            prices=[LabeledPrice(label=product.name[:32] or "Товар", amount=int(product.stars_price))],
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при создании инвойса Stars: {e}")
        await callback.message.answer(
            "❌ <b>Не удалось создать инвойс на оплату звездами</b>\n\nПопробуйте позже или выберите оплату с баланса.",
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()


@router.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery, transaction_repo: TransactionRepository):
    """Подтверждаем pre-checkout для Stars инвойсов."""
    try:
        if pre_checkout_query.invoice_payload and pre_checkout_query.invoice_payload.startswith("stars:"):
            await pre_checkout_query.answer(ok=True)
        else:
            await pre_checkout_query.answer(ok=False, error_message="Некорректный платеж")
    except Exception as e:
        logger.error(f"Ошибка в pre_checkout: {e}")
        try:
            await pre_checkout_query.answer(ok=False, error_message="Ошибка обработки платежа")
        except Exception:
            pass


@router.message(F.successful_payment)
async def on_successful_payment(
    message: Message,
    product_repo: ProductRepository,
    transaction_repo: TransactionRepository,
    product_item_repo: ProductItemRepository,
    user_repo: UserRepository,
):
    """Завершение покупки за звезды: выдача позиции и чек."""
    sp = message.successful_payment
    payload = sp.invoice_payload or ""
    try:
        if not payload.startswith("stars:"):
            return
        _, product_id, transaction_id = payload.split(":")
        product = await product_repo.get_product(product_id)
        transaction = await transaction_repo.get_transaction(transaction_id)
        if not product:
            await message.answer("❌ Товар не найден", parse_mode=ParseMode.HTML)
            return
        # Обновляем транзакцию
        if transaction and transaction.status != "completed":
            transaction.status = "completed"
            await transaction_repo.update_transaction(transaction)
        # Выбираем и помечаем позицию
        available_items = await product_item_repo.get_available_items(product_id)
        receipt_id = transaction.receipt_id if transaction and transaction.receipt_id else sp.telegram_payment_charge_id
        data_block = ""
        if available_items:
            item = available_items[0]
            await product_item_repo.mark_as_sold(item.id, message.from_user.id, receipt_id=receipt_id)
            await product_item_repo.update_product_quantity_from_items(product_id)
            # Кнопка копирования: отдельным сообщением, а в чеке — красиво в код-блоке
            data_block = f"📦 <b>Ваши данные:</b>\n<code>{item.data}</code>\n\n"
        # Обновляем метрики
        await product_repo.increment_sales(product_id)
        await user_repo.increment_purchases(message.from_user.id)
        # Чек
        receipt_text = (
            f"🧾 <b>Чек #{receipt_id}</b>\n\n"
            f"📦 Товар: <b>{product.name}</b>\n"
            f"✨ Сумма: <b>{int(product.stars_price)} ⭐</b>\n"
            f"✅ Статус: <b>Оплачено звездами</b>\n\n"
        )
        if product.description:
            import re
            clean_description = re.sub(r"<[^>]+>", "", product.description)
            clean_description = (
                clean_description.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            receipt_text += f"📝 Описание товара:\n{clean_description}\n\n"
        receipt_text += data_block
        if product.instruction_link:
            receipt_text += f"📖 <b>Инструкция:</b> <a href='{product.instruction_link}'>Ссылка на инструкцию</a>\n\n"
        await message.answer(receipt_text + "Спасибо за покупку! ✨", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Ошибка обработки успешной оплаты Stars: {e}")
        await message.answer("❌ Ошибка при обработке платежа звездами", parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "products:list")
async def back_to_products(callback: CallbackQuery, product_repo: ProductRepository):
    """Возврат к списку товаров"""
    products = await product_repo.get_all_products(available_only=True)
    
    try:
        await callback.message.edit_text(
            "🛒 <b>Выберите товар для покупки:</b>",
            reply_markup=get_products_keyboard(products),
            parse_mode=ParseMode.HTML
        )
    except TelegramBadRequest as e:
        # Если не удается отредактировать сообщение (например, это сообщение с фото),
        # отправляем новое сообщение
        logger.warning(f"Не удалось отредактировать сообщение в back_to_products: {e}")
        await callback.message.answer(
            "🛒 <b>Выберите товар для покупки:</b>",
            reply_markup=get_products_keyboard(products),
            parse_mode=ParseMode.HTML
        )
        # Удаляем старое сообщение, если возможно
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
    except Exception as e:
        # Обработка любых других исключений
        logger.error(f"Неожиданная ошибка в back_to_products: {e}")
        await callback.message.answer(
            "🛒 <b>Выберите товар для покупки:</b>",
            reply_markup=get_products_keyboard(products),
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("buy:"))
async def start_purchase(callback: CallbackQuery, state: FSMContext, product_repo: ProductRepository, user_repo: UserRepository):
    """Начало процесса покупки"""
    product_id = callback.data.split(":")[1]
    product = await product_repo.get_product(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    if product.quantity <= 0:
        await callback.answer("❌ Товар закончился", show_alert=True)
        return
    
    # Получаем пользователя и проверяем баланс
    user = await user_repo.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    if user.balance < product.price:
        try:
            await callback.message.edit_text(
                f"❌ Недостаточно средств\n\n"
                f"📦 Товар: {product.name}\n"
                f"💰 Цена: {product.price:.2f}₽\n"
                f"💳 Ваш баланс: {user.balance:.2f}₽\n\n"
                f"Необходимо пополнить баланс на {product.price - user.balance:.2f}₽",
                reply_markup=get_products_keyboard([]),
                parse_mode=ParseMode.HTML
            )
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось отредактировать сообщение при недостатке средств: {e}")
            await callback.message.answer(
                f"❌ Недостаточно средств\n\n"
                f"📦 Товар: {product.name}\n"
                f"💰 Цена: {product.price:.2f}₽\n"
                f"💳 Ваш баланс: {user.balance:.2f}₽\n\n"
                f"Необходимо пополнить баланс на {product.price - user.balance:.2f}₽",
                reply_markup=get_products_keyboard([]),
                parse_mode=ParseMode.HTML
            )
            # Удаляем старое сообщение, если возможно
            try:
                await callback.message.delete()
            except TelegramBadRequest:
                pass
        await callback.answer()
        return
    
    # Создаем клавиатуру подтверждения покупки
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="✅ Подтвердить покупку", callback_data=f"confirm_purchase:{product_id}"))
    kb.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_purchase"))
    
    try:
        await callback.message.edit_text(
            f"🛒 Подтверждение покупки\n\n"
            f"📦 Товар: {product.name}\n"
            f"💰 Цена: {product.price:.2f}₽\n"
            f"💳 Ваш баланс: {user.balance:.2f}₽\n"
            f"💳 Остаток после покупки: {user.balance - product.price:.2f}₽\n\n"
            f"Подтвердите покупку:",
            reply_markup=kb.as_markup(),
            parse_mode=ParseMode.HTML
        )
    except TelegramBadRequest as e:
        logger.error(f"Ошибка при редактировании сообщения в start_purchase: {e}")
        await callback.message.answer(
            f"🛒 Подтверждение покупки\n\n"
            f"📦 Товар: {product.name}\n"
            f"💰 Цена: {product.price:.2f}₽\n"
            f"💳 Ваш баланс: {user.balance:.2f}₽\n"
            f"💳 Остаток после покупки: {user.balance - product.price:.2f}₽\n\n"
            f"Подтвердите покупку:",
            reply_markup=kb.as_markup(),
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_purchase:"))
async def confirm_purchase(callback: CallbackQuery, product_repo: ProductRepository, user_repo: UserRepository, transaction_repo: TransactionRepository, product_item_repo: ProductItemRepository):
    """Подтверждение покупки с баланса"""
    product_id = callback.data.split(":")[1]
    product = await product_repo.get_product(product_id)
    user = await user_repo.get_user(callback.from_user.id)
    
    if not product or not user:
        await callback.answer("❌ Ошибка: товар или пользователь не найден", show_alert=True)
        return
    
    if product.quantity <= 0:
        await callback.answer("❌ Товар закончился", show_alert=True)
        return
    
    if user.balance < product.price:
        await callback.answer("❌ Недостаточно средств", show_alert=True)
        return
    
    try:
        # Создаем транзакцию покупки
        import uuid
        receipt_id = f"{uuid.uuid4().hex[:16]}"
        
        transaction = await transaction_repo.create_transaction(
            user_id=callback.from_user.id,
            amount=product.price,
            transaction_type="purchase",
            status="completed",
            payment_method="balance",
            product_id=product_id,
            receipt_id=receipt_id
        )
        
        # Списываем средства с баланса
        await user_repo.update_balance(callback.from_user.id, -product.price)
        
        # Уменьшаем количество товара
        await product_repo.update_quantity(product_id, -1)
        
        # Увеличиваем счетчик продаж товара
        await product_repo.increment_sales(product_id)
        
        # Увеличиваем счетчик покупок пользователя
        await user_repo.increment_purchases(callback.from_user.id)
        
        # Формируем текст с информацией о покупке
        receipt_text = (
            f"🧾 Чек #{transaction.receipt_id}\n\n"
            f"📦 Товар: {product.name}\n"
            f"💰 Сумма: {transaction.amount:.2f}₽\n"
            f"📅 Дата: {transaction.created_at.strftime('%d.%m.%Y %H:%M:%S')}\n\n"
            f"✅ Статус: Оплачено с баланса\n\n"
        )
        
        # Если у товара есть описание, добавляем его в чек
        if product.description:
            # Очищаем описание от некорректных HTML-тегов
            import re
            clean_description = re.sub(r'<[^>]+>', '', product.description)
            clean_description = clean_description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            receipt_text += f"📝 Описание товара:\n{clean_description}\n\n"
        
        # Получаем доступные позиции товара
        available_items = await product_item_repo.get_available_items(product_id)
        
        if available_items:
            # Выбираем первую доступную позицию
            item = available_items[0]
            
            # Помечаем позицию как проданную и связываем с чеком
            await product_item_repo.mark_as_sold(item.id, callback.from_user.id, receipt_id=transaction.receipt_id)
            
            # Обновляем количество товара
            await product_item_repo.update_product_quantity_from_items(product_id)
            
            # Добавляем данные товара в чек
            receipt_text += f"📦 <b>Ваши данные:</b>\n<code>{item.data}</code>\n\n"
            
            # Если есть инструкция, добавляем её
            if product.instruction_link:
                receipt_text += f"📖 <b>Инструкция:</b> <a href='{product.instruction_link}'>Ссылка на инструкцию</a>\n\n"
        
        try:
            await callback.message.edit_text(
                receipt_text + "Спасибо за покупку! 🎉",
                parse_mode=ParseMode.HTML
            )
        except TelegramBadRequest as e:
            logger.error(f"Ошибка при редактировании сообщения в confirm_purchase: {e}")
            await callback.message.answer(
                receipt_text + "Спасибо за покупку! 🎉",
                parse_mode=ParseMode.HTML
            )
        
        await callback.answer("✅ Покупка успешно совершена", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка при совершении покупки: {e}")
        await callback.answer("❌ Произошла ошибка при покупке", show_alert=True)


@router.callback_query(F.data == "cancel_purchase")
async def cancel_purchase(callback: CallbackQuery, product_repo: ProductRepository):
    """Отмена покупки"""
    products = await product_repo.get_all_products(available_only=True)
    
    try:
        await callback.message.edit_text(
            "❌ <b>Покупка отменена</b>\n\n"
            "Вы можете вернуться к списку товаров или выбрать другой товар.",
            reply_markup=get_products_keyboard(products),
            parse_mode=ParseMode.HTML
        )
    except TelegramBadRequest as e:
        # Если не удается отредактировать сообщение, отправляем новое
        logger.warning(f"Не удалось отредактировать сообщение в cancel_purchase: {e}")
        await callback.message.answer(
            "❌ <b>Покупка отменена</b>\n\n"
            "Вы можете вернуться к списку товаров или выбрать другой товар.",
            reply_markup=get_products_keyboard(products),
            parse_mode=ParseMode.HTML
        )
        # Удаляем старое сообщение, если возможно
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
    
    await callback.answer()


@router.callback_query(BuyProduct.select_payment_method, F.data.startswith("pay:crypto:"))
async def crypto_payment(
    callback: CallbackQuery, 
    state: FSMContext, 
    config: Config, 
    product_repo: ProductRepository,
    user_repo: UserRepository,
    transaction_repo: TransactionRepository
):
    """Оплата криптовалютой"""
    # Получаем данные из состояния
    data = await state.get_data()
    product_id = data.get("product_id")
    product_name = data.get("product_name")
    product_price = data.get("product_price")
    
    # Получаем товар
    product = await product_repo.get_product(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        await state.clear()
        return
    
    if product.quantity <= 0:
        await callback.answer("❌ Товар закончился", show_alert=True)
        await state.clear()
        return
    
    # Получаем выбранную криптовалюту
    crypto = callback.data.split(":")[-1]
    
    # Проверяем наличие токена Crypto Pay
    settings_service = SettingsService()
    crypto_pay_token = await settings_service.get_crypto_pay_token()
    
    if not crypto_pay_token:
        try:
            await callback.message.edit_text(
                "❌ <b>Оплата криптовалютой временно недоступна</b>\n\n"
                "Пожалуйста, выберите другой способ оплаты или попробуйте позже.",
                reply_markup=get_payment_method_keyboard(),
                parse_mode=ParseMode.HTML
            )
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось отредактировать сообщение при недоступности Crypto Pay: {e}")
            await callback.message.answer(
                "❌ <b>Оплата криптовалютой временно недоступна</b>\n\n"
                "Пожалуйста, выберите другой способ оплаты или попробуйте позже.",
                reply_markup=get_payment_method_keyboard(),
                parse_mode=ParseMode.HTML
            )
            try:
                await callback.message.delete()
            except TelegramBadRequest:
                pass
        await callback.answer()
        return
    
    try:
        # Создаем сервис для работы с Crypto Pay
        crypto_pay = CryptoPayService(
            api_token=crypto_pay_token,
            testnet=config.payment.crypto_pay_testnet
        )
        
        # Генерируем уникальный идентификатор для чека
        receipt_id = f"{uuid.uuid4().hex[:16]}"
        
        # Создаем транзакцию в базе данных
        transaction = await transaction_repo.create_transaction(
            user_id=callback.from_user.id,
            amount=product_price,
            transaction_type="purchase",
            status="pending",
            payment_method=f"crypto_{crypto.lower()}",
            product_id=product_id,
            receipt_id=receipt_id
        )
        
        # Сохраняем ID транзакции в состоянии
        await state.update_data(transaction_id=str(transaction.id))
        
        # Создаем инвойс в Crypto Pay
        invoice = await crypto_pay.create_invoice(
            amount=product_price,
            asset=crypto,
            description=f"Покупка {product_name}",
            payload=str(transaction.id),
            allow_comments=False,
            allow_anonymous=False
        )
        
        # Обновляем транзакцию с ID платежа
        transaction.payment_id = invoice.get("invoice_id")
        await transaction_repo.update_transaction(transaction)
        
        # Сохраняем ID инвойса в состоянии
        await state.update_data(invoice_id=invoice.get("invoice_id"))
        
        # Формируем URL для оплаты
        pay_url = invoice.get("pay_url")
        
        # Переходим к ожиданию оплаты
        await state.set_state(BuyProduct.waiting_payment)
        
        try:
            await callback.message.edit_text(
                f"💰 <b>Оплата заказа</b>\n\n"
                f"📦 Товар: <b>{product_name}</b>\n"
                f"💰 Сумма: <b>{product_price:.2f}₽</b>\n"
                f"💱 Валюта: <b>{crypto}</b>\n\n"
                f"Для оплаты перейдите по <a href='{pay_url}'>ссылке</a> и следуйте инструкциям.\n"
                f"После оплаты нажмите кнопку «Проверить оплату».\n\n"
                f"Номер заказа: <code>{receipt_id}</code>",
                reply_markup=get_confirm_purchase_keyboard(),
                parse_mode=ParseMode.HTML
            )
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось отредактировать сообщение при создании инвойса: {e}")
            await callback.message.answer(
                f"💰 <b>Оплата заказа</b>\n\n"
                f"📦 Товар: <b>{product_name}</b>\n"
                f"💰 Сумма: <b>{product_price:.2f}₽</b>\n"
                f"💱 Валюта: <b>{crypto}</b>\n\n"
                f"Для оплаты перейдите по <a href='{pay_url}'>ссылке</a> и следуйте инструкциям.\n"
                f"После оплаты нажмите кнопку «Проверить оплату».\n\n"
                f"Номер заказа: <code>{receipt_id}</code>",
                reply_markup=get_confirm_purchase_keyboard(),
                parse_mode=ParseMode.HTML
            )
            try:
                await callback.message.delete()
            except TelegramBadRequest:
                pass
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при создании инвойса: {e}")
        try:
            await callback.message.edit_text(
                "❌ <b>Произошла ошибка при создании счета на оплату</b>\n\n"
                "Пожалуйста, попробуйте позже или выберите другой способ оплаты.",
                reply_markup=get_payment_method_keyboard(),
                parse_mode=ParseMode.HTML
            )
        except TelegramBadRequest as edit_error:
            logger.warning(f"Не удалось отредактировать сообщение при ошибке создания инвойса: {edit_error}")
            await callback.message.answer(
                "❌ <b>Произошла ошибка при создании счета на оплату</b>\n\n"
                "Пожалуйста, попробуйте позже или выберите другой способ оплаты.",
                reply_markup=get_payment_method_keyboard(),
                parse_mode=ParseMode.HTML
            )
            try:
                await callback.message.delete()
            except TelegramBadRequest:
                pass
        await callback.answer()


@router.callback_query(BuyProduct.select_payment_method, F.data.startswith("pay:card:"))
async def card_payment(callback: CallbackQuery, state: FSMContext):
    """Оплата картой"""
    # В данной версии бота оплата картой не реализована
    await callback.message.edit_text(
        "❌ <b>Оплата картой временно недоступна</b>\n\n"
        "Пожалуйста, выберите другой способ оплаты или попробуйте позже.",
        reply_markup=get_payment_method_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(BuyProduct.select_payment_method, F.data == "pay:cancel")
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    """Отмена оплаты"""
    await state.clear()
    
    try:
        await callback.message.edit_text(
            "❌ <b>Оплата отменена</b>\n\n"
            "Вы можете вернуться к списку товаров или выбрать другой товар.",
            reply_markup=get_products_keyboard([]),
            parse_mode=ParseMode.HTML
        )
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отредактировать сообщение в cancel_payment: {e}")
        await callback.message.answer(
            "❌ <b>Оплата отменена</b>\n\n"
            "Вы можете вернуться к списку товаров или выбрать другой товар.",
            reply_markup=get_products_keyboard([]),
            parse_mode=ParseMode.HTML
        )
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
    
    await callback.answer()


@router.callback_query(BuyProduct.waiting_payment, F.data.startswith("confirm:"))
async def check_payment(
    callback: CallbackQuery, 
    state: FSMContext, 
    config: Config, 
    product_repo: ProductRepository,
    transaction_repo: TransactionRepository,
    user_repo: UserRepository,
    product_item_repo: ProductItemRepository
):
    """Проверка статуса оплаты"""
    # Получаем данные из состояния
    data = await state.get_data()
    transaction_id = data.get("transaction_id")
    invoice_id = data.get("invoice_id")
    product_id = data.get("product_id")
    
    # Получаем транзакцию
    transaction = await transaction_repo.get_transaction(transaction_id)
    
    if not transaction:
        await callback.answer("❌ Транзакция не найдена", show_alert=True)
        await state.clear()
        return
    
    # Получаем товар
    product = await product_repo.get_product(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        await state.clear()
        return
    
    # Проверяем статус оплаты
    settings_service = SettingsService()
    crypto_pay_token = await settings_service.get_crypto_pay_token()
    
    if not crypto_pay_token:
        await callback.answer("❌ Невозможно проверить статус оплаты", show_alert=True)
        return
    
    try:
        # Создаем сервис для работы с Crypto Pay
        crypto_pay = CryptoPayService(
            api_token=crypto_pay_token,
            testnet=config.payment.crypto_pay_testnet
        )
        
        # Получаем информацию об инвойсе
        invoices = await crypto_pay.get_invoices(invoice_ids=[invoice_id])
        
        if not invoices:
            await callback.answer("❌ Счет на оплату не найден", show_alert=True)
            return
        
        invoice = invoices[0]
        status = invoice.get("status")
        
        if status == "paid":
            # Обновляем статус транзакции
            transaction.status = "completed"
            await transaction_repo.update_transaction(transaction)
            
            # Уменьшаем количество товара
            await product_repo.update_quantity(product_id, -1)
            
            # Увеличиваем счетчик продаж товара
            await product_repo.increment_sales(product_id)
            
            # Увеличиваем счетчик покупок пользователя
            await user_repo.increment_purchases(callback.from_user.id)
            
            # Формируем текст с информацией о покупке
            receipt_text = (
                f"🧾 <b>Чек #{transaction.receipt_id}</b>\n\n"
                f"📦 Товар: <b>{product.name}</b>\n"
                f"💰 Сумма: <b>{transaction.amount:.2f}₽</b>\n"
                f"📅 Дата: {transaction.created_at.strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                f"✅ Статус: <b>Оплачено</b>\n\n"
            )
            
            # Если у товара есть описание, добавляем его в чек
            if product.description:
                # Очищаем описание от некорректных HTML-тегов
                import re
                clean_description = re.sub(r'<[^>]+>', '', product.description)
                clean_description = clean_description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                receipt_text += f"📝 Описание товара:\n{clean_description}\n\n"
            
            # Получаем доступные позиции товара
            available_items = await product_item_repo.get_available_items(product_id)
            
            if available_items:
                # Выбираем первую доступную позицию
                item = available_items[0]
                
                # Помечаем позицию как проданную и связываем с чеком
                await product_item_repo.mark_as_sold(item.id, callback.from_user.id, receipt_id=transaction.receipt_id)
                
                # Обновляем количество товара
                await product_item_repo.update_product_quantity_from_items(product_id)
                
                # Добавляем данные товара в чек
                receipt_text += f"📦 <b>Ваши данные:</b>\n<code>{item.data}</code>\n\n"
                
                # Если есть инструкция, добавляем её
                if product.instruction_link:
                    receipt_text += f"📖 <b>Инструкция:</b> <a href='{product.instruction_link}'>Ссылка на инструкцию</a>\n\n"
            
            # Очищаем состояние
            await state.clear()
            
            try:
                await callback.message.edit_text(
                    receipt_text + "Спасибо за покупку! 🎉",
                    parse_mode=ParseMode.HTML
                )
            except TelegramBadRequest as e:
                logger.error(f"Ошибка при редактировании сообщения в check_payment: {e}")
                await callback.message.answer(
                    receipt_text + "Спасибо за покупку! 🎉",
                    parse_mode=ParseMode.HTML
                )
            
            await callback.answer("✅ Оплата подтверждена", show_alert=True)
            
        elif status == "active":
            # Счет еще не оплачен
            await callback.answer("❌ Оплата еще не поступила", show_alert=True)
            
        else:
            # Счет отменен или просрочен
            transaction.status = "canceled"
            await transaction_repo.update_transaction(transaction)
            
            try:
                await callback.message.edit_text(
                    "❌ <b>Счет на оплату отменен или просрочен</b>\n\n"
                    "Вы можете вернуться к списку товаров или выбрать другой товар.",
                    reply_markup=get_products_keyboard([]),
                    parse_mode=ParseMode.HTML
                )
            except TelegramBadRequest as e:
                logger.error(f"Ошибка при редактировании сообщения в check_payment (canceled): {e}")
                await callback.message.answer(
                    "❌ <b>Счет на оплату отменен или просрочен</b>\n\n"
                    "Вы можете вернуться к списку товаров или выбрать другой товар.",
                    reply_markup=get_products_keyboard([]),
                    parse_mode=ParseMode.HTML
                )
            
            await callback.answer()
            await state.clear()
            
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса оплаты: {e}")
        await callback.answer("❌ Произошла ошибка при проверке оплаты", show_alert=True)


@router.callback_query(F.data == "cancel")
async def cancel_operation(callback: CallbackQuery, state: FSMContext):
    """Отмена операции"""
    current_state = await state.get_state()
    
    if current_state:
        await state.clear()
    
    try:
        await callback.message.edit_text(
            "❌ <b>Операция отменена</b>\n\n"
            "Вы можете вернуться к списку товаров или выбрать другой товар.",
            reply_markup=get_products_keyboard([]),
            parse_mode=ParseMode.HTML
        )
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отредактировать сообщение в cancel_operation: {e}")
        await callback.message.answer(
            "❌ <b>Операция отменена</b>\n\n"
            "Вы можете вернуться к списку товаров или выбрать другой товар.",
            reply_markup=get_products_keyboard([]),
            parse_mode=ParseMode.HTML
        )
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
    
    await callback.answer()