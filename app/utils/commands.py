from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat


async def set_bot_commands(bot: Bot):
    """Установка команд бота"""
    
    # Основные команды для всех пользователей
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="help", description="Помощь по боту"),
            BotCommand(command="profile", description="Мой профиль"),
            BotCommand(command="buy", description="Купить товары"),
            BotCommand(command="products", description="Список доступных товаров"),
            BotCommand(command="support", description="Связаться с поддержкой"),
        ],
        scope=BotCommandScopeDefault()
    )


async def set_admin_commands(bot: Bot, admin_id: int):
    """Установка команд для администраторов"""
    
    # Команды для администраторов
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="help", description="Помощь по боту"),
            BotCommand(command="profile", description="Мой профиль"),
            BotCommand(command="buy", description="Купить товары"),
            BotCommand(command="products", description="Список доступных товаров"),
            BotCommand(command="support", description="Связаться с поддержкой"),
            # Админские команды
            BotCommand(command="settings", description="Настройки бота"),
            BotCommand(command="stats", description="Статистика магазина"),
            BotCommand(command="add_product", description="Добавить товар"),
            BotCommand(command="backup", description="Создать резервную копию"),
        ],
        scope=BotCommandScopeChat(chat_id=admin_id)
    )