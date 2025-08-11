from typing import Dict, Any, Awaitable, Callable, Optional
import time

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, CallbackQuery
from cachetools import TTLCache
from loguru import logger


class ThrottlingMiddleware(BaseMiddleware):
    """Middleware для ограничения частоты запросов (защита от спама)"""
    
    def __init__(self, rate_limit: int):
        # Максимальное количество запросов в секунду
        self.rate_limit = rate_limit
        
        # Кэш для хранения времени последних запросов пользователей
        # TTL (time-to-live) в секундах, максимальный размер кэша
        self.cache = TTLCache(maxsize=10000, ttl=60)
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Optional[Any]:
        # Работаем с сообщениями и callback-запросами
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await handler(event, data)
        
        # Проверяем, есть ли пользователь в кэше
        if user_id in self.cache:
            # Получаем список времени последних запросов
            requests = self.cache[user_id]
            
            # Текущее время
            now = time.time()
            
            # Удаляем запросы старше 1 секунды
            requests = [t for t in requests if now - t < 1]
            
            # Если количество запросов превышает лимит
            if len(requests) >= self.rate_limit:
                logger.warning(f"Throttling applied for user {user_id}")
                return None
            
            # Добавляем текущий запрос
            requests.append(now)
            self.cache[user_id] = requests
        else:
            # Если пользователя нет в кэше, добавляем его
            self.cache[user_id] = [time.time()]
        
        # Вызываем следующий обработчик
        return await handler(event, data)