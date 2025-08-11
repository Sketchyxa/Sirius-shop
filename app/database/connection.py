from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger

from app.config import DbConfig


async def setup_mongodb(config: DbConfig) -> AsyncIOMotorClient:
    """Настройка подключения к MongoDB"""
    try:
        client = AsyncIOMotorClient(config.uri)
        # Проверка соединения
        await client.admin.command('ping')
        logger.info(f"Успешное подключение к MongoDB: {config.uri}")
        return client
    except Exception as e:
        logger.error(f"Ошибка подключения к MongoDB: {e}")
        raise