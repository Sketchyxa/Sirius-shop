from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import Config
from app.middlewares.config import ConfigMiddleware
from app.middlewares.db import DatabaseMiddleware
from app.middlewares.throttling import ThrottlingMiddleware


def setup_middlewares(dp: Dispatcher, config: Config, mongo_client: AsyncIOMotorClient) -> None:
    """Настройка всех middleware для диспетчера"""
    
    # Middleware для передачи конфигурации
    dp.update.outer_middleware(ConfigMiddleware(config))
    
    # Middleware для базы данных
    db = mongo_client[config.db.name]
    dp.update.outer_middleware(DatabaseMiddleware(mongo_client, config.db.name))
    
    # Middleware для ограничения запросов
    dp.message.outer_middleware(ThrottlingMiddleware(config.bot.rate_limit))