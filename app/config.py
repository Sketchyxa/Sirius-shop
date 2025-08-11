import os
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv


@dataclass
class BotConfig:
    token: str
    admin_ids: List[int]
    rate_limit: int
    backup_chat_id: int


@dataclass
class DbConfig:
    uri: str
    name: str


@dataclass
class ModeConfig:
    maintenance: bool = False
    payments_enabled: bool = True
    purchases_enabled: bool = True


@dataclass
class PaymentConfig:
    crypto_pay_token: str = ""
    crypto_pay_testnet: bool = True


@dataclass
class Config:
    bot: BotConfig
    db: DbConfig
    mode: ModeConfig
    payment: PaymentConfig


def load_config() -> Config:
    """Загрузка конфигурации из .env файла"""
    load_dotenv()

    # Конфигурация бота
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN не задан в .env файле")

    admin_ids_str = os.getenv("ADMIN_IDS", "")
    admin_ids = [int(admin_id.strip()) for admin_id in admin_ids_str.split(",") if admin_id.strip()]

    rate_limit = int(os.getenv("RATE_LIMIT", "5"))
    backup_chat_id = int(os.getenv("BACKUP_CHAT_ID", "0"))

    # Конфигурация базы данных
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGO_DB_NAME", "siriushop")

    return Config(
        bot=BotConfig(
            token=bot_token,
            admin_ids=admin_ids,
            rate_limit=rate_limit,
            backup_chat_id=backup_chat_id
        ),
        db=DbConfig(
            uri=mongo_uri,
            name=mongo_db_name
        ),
        mode=ModeConfig(),  # Значения по умолчанию, будут загружены из базы данных
        payment=PaymentConfig()  # Значения по умолчанию, будут загружены из базы данных
    )