from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from loguru import logger


class SettingsService:
    """Сервис для работы с настройками бота"""
    
    def __init__(self, db: AsyncIOMotorDatabase = None):
        self.db = db
    
    def set_db(self, db: AsyncIOMotorDatabase):
        """Установить соединение с базой данных"""
        self.db = db
    
    async def _get_settings(self) -> Dict[str, Any]:
        """Получение текущих настроек из базы данных"""
        settings = await self.db.settings.find_one({"_id": "bot_settings"})
        if not settings:
            # Создаем настройки по умолчанию, если их нет
            default_settings = {
                "_id": "bot_settings",
                "maintenance": False,
                "payments_enabled": True,
                "purchases_enabled": True,
                "crypto_pay_token": "",
                "crypto_pay_testnet": True
            }
            await self.db.settings.insert_one(default_settings)
            return default_settings
        return settings
    
    async def _update_setting(self, key: str, value: Any) -> None:
        """Обновление значения настройки"""
        await self.db.settings.update_one(
            {"_id": "bot_settings"},
            {"$set": {key: value}},
            upsert=True
        )
        logger.info(f"Обновлена настройка {key}")
    
    async def get_maintenance_mode(self) -> bool:
        """Получение статуса режима технических работ"""
        settings = await self._get_settings()
        return settings.get("maintenance", False)
    
    async def set_maintenance_mode(self, enabled: bool) -> None:
        """Установка режима технических работ"""
        await self._update_setting("maintenance", enabled)
    
    async def get_payments_enabled(self) -> bool:
        """Получение статуса возможности пополнений"""
        settings = await self._get_settings()
        return settings.get("payments_enabled", True)
    
    async def set_payments_enabled(self, enabled: bool) -> None:
        """Установка возможности пополнений"""
        await self._update_setting("payments_enabled", enabled)
    
    async def get_purchases_enabled(self) -> bool:
        """Получение статуса возможности покупок"""
        settings = await self._get_settings()
        return settings.get("purchases_enabled", True)
    
    async def set_purchases_enabled(self, enabled: bool) -> None:
        """Установка возможности покупок"""
        await self._update_setting("purchases_enabled", enabled)
    
    async def get_crypto_pay_token(self) -> str:
        """Получение токена Crypto Pay"""
        settings = await self._get_settings()
        return settings.get("crypto_pay_token", "")
    
    async def set_crypto_pay_token(self, token: str) -> None:
        """Установка токена Crypto Pay"""
        await self._update_setting("crypto_pay_token", token)
    
    async def get_crypto_pay_testnet(self) -> bool:
        """Получение режима тестовой сети Crypto Pay"""
        settings = await self._get_settings()
        return settings.get("crypto_pay_testnet", True)
    
    async def set_crypto_pay_testnet(self, enabled: bool) -> None:
        """Установка режима тестовой сети Crypto Pay"""
        await self._update_setting("crypto_pay_testnet", enabled)
    
    async def load_settings_to_config(self, config) -> None:
        """Загрузка настроек из базы данных в конфигурацию"""
        settings = await self._get_settings()
        config.mode.maintenance = settings.get("maintenance", False)
        config.mode.payments_enabled = settings.get("payments_enabled", True)
        config.mode.purchases_enabled = settings.get("purchases_enabled", True)
        config.payment.crypto_pay_token = settings.get("crypto_pay_token", "")
        config.payment.crypto_pay_testnet = settings.get("crypto_pay_testnet", True)
        logger.info("Настройки загружены из базы данных")