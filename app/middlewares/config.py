from typing import Dict, Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.config import Config


class ConfigMiddleware(BaseMiddleware):
    """Middleware для передачи конфигурации в обработчики"""
    
    def __init__(self, config: Config):
        self.config = config
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Добавляем конфигурацию в данные
        data["config"] = self.config
        
        # Вызываем следующий обработчик
        return await handler(event, data)