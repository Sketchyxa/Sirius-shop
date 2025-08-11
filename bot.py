import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage


from loguru import logger

from app.config import load_config
from app.database.connection import setup_mongodb
from app.middlewares.setup import setup_middlewares
from app.handlers.setup import setup_all_handlers
from app.utils.logging import setup_logging
from app.utils.commands import set_bot_commands


async def main():
    # Настройка логирования
    setup_logging()
    logger.info("Бот запускается...")

    # Загрузка конфигурации
    config = load_config()
    logger.info("Конфигурация загружена")

    # Инициализация хранилища состояний
    storage = MemoryStorage()
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.bot.token)
    dp = Dispatcher(storage=storage)

    # Подключение к базе данных
    mongo_client = await setup_mongodb(config.db)
    logger.info("Подключение к MongoDB установлено")

    # Регистрация всех обработчиков
    await setup_all_handlers(dp)
    logger.info("Обработчики зарегистрированы")

    # Настройка middleware
    setup_middlewares(dp, config, mongo_client)
    logger.info("Middleware настроены")

    # Установка команд бота
    await set_bot_commands(bot)
    logger.info("Команды бота установлены")

    # Запуск поллинга
    logger.info("Бот запущен")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)