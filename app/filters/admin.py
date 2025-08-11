from typing import Union, Dict, Any, Optional

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from app.config import Config


class AdminFilter(BaseFilter):
    """Фильтр для проверки, является ли пользователь администратором"""
    
    async def __call__(self, event: Union[Message, CallbackQuery], config: Config) -> bool:
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return False
        
        return user_id in config.bot.admin_ids