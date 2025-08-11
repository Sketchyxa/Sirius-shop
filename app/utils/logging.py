import logging
import sys
import os
from pathlib import Path
from loguru import logger


def setup_logging():
    """Настройка логирования с использованием loguru"""
    
    # Создаем директорию для логов, если её нет
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Добавляем обработчик для вывода в консоль (только INFO и выше)
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # Добавляем обработчик для записи всех логов в файл
    logger.add(
        "logs/bot.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",  # Новый файл при достижении 10 МБ
        compression="zip",  # Сжимать старые файлы
        retention="1 week"  # Хранить логи 1 неделю
    )
    
    # Добавляем отдельный файл для важных логов (INFO и выше)
    logger.add(
        "logs/info.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        rotation="5 MB",
        compression="zip",
        retention="2 weeks"
    )
    
    # Добавляем отдельный файл для ошибок
    logger.add(
        "logs/errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="1 MB",
        compression="zip",
        retention="1 month"
    )
    
    # Перехватываем логи стандартной библиотеки logging
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Получаем соответствующий уровень loguru
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            
            # Находим вызывающий код
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            
            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )
    
    # Настраиваем перехват для всех логгеров
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    
    # Устанавливаем перехватчик для aiogram и других библиотек
    for log_name in ["aiogram", "motor", "pymongo", "aiohttp"]:
        logging.getLogger(log_name).handlers = [InterceptHandler()]
        
    logger.info("Система логирования настроена")