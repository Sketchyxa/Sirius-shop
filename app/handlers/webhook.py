import hashlib
import hmac
import json
from typing import Dict, Any

from aiohttp import web
from loguru import logger

from app.config import Config
from app.database.repositories import UserRepository, ProductRepository, PurchaseRepository
from app.database.models import Purchase


class CryptoPayWebhook:
    """Обработчик вебхуков от Crypto Pay"""
    
    def __init__(self, config: Config, user_repo: UserRepository, product_repo: ProductRepository, purchase_repo: PurchaseRepository):
        self.config = config
        self.user_repo = user_repo
        self.product_repo = product_repo
        self.purchase_repo = purchase_repo
        
        # Создаем секретный ключ для проверки подписи
        self.secret_key = hashlib.sha256(config.payment.crypto_pay_token.encode()).digest()
    
    def verify_signature(self, body: str, signature: str) -> bool:
        """
        Проверка подписи запроса от Crypto Pay
        
        Args:
            body: Тело запроса (JSON строка)
            signature: Подпись запроса
            
        Returns:
            bool: True, если подпись верна
        """
        computed_signature = hmac.new(
            key=self.secret_key,
            msg=body.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(computed_signature, signature)
    
    async def process_webhook(self, request: web.Request) -> web.Response:
        """
        Обработка вебхука от Crypto Pay
        
        Args:
            request: Запрос
            
        Returns:
            web.Response: Ответ
        """
        try:
            # Получаем тело запроса
            body = await request.text()
            data = await request.json()
            
            # Получаем подпись
            signature = request.headers.get("crypto-pay-api-signature")
            
            # Проверяем подпись
            if not signature or not self.verify_signature(body, signature):
                logger.warning("Неверная подпись вебхука Crypto Pay")
                return web.Response(status=401, text="Invalid signature")
            
            # Проверяем тип обновления
            if data.get("update_type") != "invoice_paid":
                logger.info(f"Получен вебхук с типом: {data.get('update_type')}")
                return web.Response(status=200, text="OK")
            
            # Обрабатываем оплаченный счет
            await self._handle_invoice_paid(data.get("payload", {}))
            
            return web.Response(status=200, text="OK")
        
        except Exception as e:
            logger.error(f"Ошибка при обработке вебхука Crypto Pay: {e}")
            return web.Response(status=500, text="Internal Server Error")
    
    async def _handle_invoice_paid(self, invoice: Dict[str, Any]) -> None:
        """
        Обработка оплаченного счета
        
        Args:
            invoice: Данные счета
        """
        try:
            # Проверяем статус счета
            if invoice.get("status") != "paid":
                return
            
            # Получаем payload
            payload = invoice.get("payload", "")
            if not payload:
                logger.warning(f"Пустой payload в оплаченном счете: {invoice.get('invoice_id')}")
                return
            
            # Разбираем payload (payment_id:product_id:user_id)
            payload_parts = payload.split(":")
            if len(payload_parts) != 3:
                logger.warning(f"Неверный формат payload: {payload}")
                return
            
            payment_id, product_id, user_id = payload_parts
            user_id = int(user_id)
            
            # Получаем товар
            product = await self.product_repo.get_product(product_id)
            if not product:
                logger.warning(f"Товар не найден: {product_id}")
                return
            
            # Уменьшаем количество товара
            product.quantity -= 1
            await self.product_repo.update_product(product)
            
            # Создаем запись о покупке
            purchase = Purchase(
                id=payment_id,
                user_id=user_id,
                product_id=product_id,
                quantity=1,
                total_price=product.price,
                status="completed"
            )
            await self.purchase_repo.create_purchase(purchase)
            
            # Обновляем информацию о пользователе
            user = await self.user_repo.get_user(user_id)
            if user:
                user.purchases += 1
                await self.user_repo.update_user(user)
            
            logger.info(f"Успешная обработка оплаты: {invoice.get('invoice_id')} от пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке оплаченного счета: {e}")


async def setup_webhook_routes(app: web.Application, config: Config, mongo_client) -> None:
    """
    Настройка маршрутов для вебхуков
    
    Args:
        app: AIOHTTP приложение
        config: Конфигурация
        mongo_client: Клиент MongoDB
    """
    from app.database.repositories import UserRepository, ProductRepository, PurchaseRepository
    
    # Создаем репозитории
    user_repo = UserRepository(mongo_client, config.db.name)
    product_repo = ProductRepository(mongo_client, config.db.name)
    purchase_repo = PurchaseRepository(mongo_client, config.db.name)
    
    # Создаем обработчик вебхуков
    webhook_handler = CryptoPayWebhook(config, user_repo, product_repo, purchase_repo)
    
    # Добавляем маршрут для вебхука
    app.router.add_post("/webhook/crypto-pay", webhook_handler.process_webhook)