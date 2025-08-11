from typing import Dict, Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from motor.motor_asyncio import AsyncIOMotorClient

from app.database.repositories import UserRepository, ProductRepository, ProductItemRepository, TransactionRepository, CategoryRepository
from app.services.settings_service import SettingsService


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для передачи репозиториев базы данных в обработчики"""
    
    def __init__(self, mongo_client: AsyncIOMotorClient, db_name: str):
        self.mongo_client = mongo_client
        self.db_name = db_name
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем базу данных
        db = self.mongo_client[self.db_name]
        
        # Создаем репозитории
        user_repo = UserRepository()
        user_repo.set_db(db)
        
        product_repo = ProductRepository()
        product_repo.set_db(db)
        
        transaction_repo = TransactionRepository()
        transaction_repo.set_db(db)
        
        category_repo = CategoryRepository()
        category_repo.set_db(db)
        
        product_item_repo = ProductItemRepository()
        product_item_repo.set_db(db)
        
        # Создаем сервис настроек
        settings_service = SettingsService()
        settings_service.set_db(db)
        
        # Добавляем репозитории и сервисы в данные
        data["user_repo"] = user_repo
        data["product_repo"] = product_repo
        data["product_item_repo"] = product_item_repo
        data["transaction_repo"] = transaction_repo
        data["category_repo"] = category_repo
        data["settings_service"] = settings_service
        
        # Вызываем следующий обработчик
        return await handler(event, data)