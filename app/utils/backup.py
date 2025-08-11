import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
import tempfile
import zipfile

from aiogram import Bot
from aiogram.types import FSInputFile
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger

from app.config import Config


async def create_backup(client: AsyncIOMotorClient, db_name: str) -> Path:
    """Создание резервной копии базы данных"""
    
    # Создаем временную директорию для резервных копий
    backup_dir = Path(tempfile.mkdtemp())
    
    # Получаем список коллекций
    collections = await client[db_name].list_collection_names()
    
    # Для каждой коллекции создаем JSON файл с данными
    for collection_name in collections:
        collection_data = []
        cursor = client[db_name][collection_name].find({})
        
        async for document in cursor:
            # Преобразуем ObjectId в строку для возможности сериализации
            if "_id" in document:
                document["_id"] = str(document["_id"])
            
            # Преобразуем datetime в строку
            for key, value in document.items():
                if isinstance(value, datetime):
                    document[key] = value.isoformat()
            
            collection_data.append(document)
        
        # Записываем данные в JSON файл
        with open(backup_dir / f"{collection_name}.json", "w", encoding="utf-8") as f:
            json.dump(collection_data, f, ensure_ascii=False, indent=2)
    
    # Создаем ZIP архив с JSON файлами
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_path = backup_dir / f"backup_{timestamp}.zip"
    
    with zipfile.ZipFile(zip_path, "w") as zip_file:
        for json_file in backup_dir.glob("*.json"):
            zip_file.write(json_file, json_file.name)
    
    return zip_path


async def send_backup_to_admin(bot: Bot, config: Config, client: AsyncIOMotorClient):
    """Отправка резервной копии администратору"""
    try:
        # Создаем резервную копию
        backup_path = await create_backup(client, config.db.name)
        
        # Отправляем файл администратору
        for admin_id in config.bot.admin_ids:
            try:
                await bot.send_document(
                    chat_id=admin_id,
                    document=FSInputFile(backup_path),
                    caption=f"📦 Резервная копия базы данных\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
                )
                logger.info(f"Резервная копия отправлена администратору {admin_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке резервной копии администратору {admin_id}: {e}")
        
        # Удаляем временные файлы
        os.unlink(backup_path)
        for json_file in Path(backup_path).parent.glob("*.json"):
            os.unlink(json_file)
        
    except Exception as e:
        logger.error(f"Ошибка при создании резервной копии: {e}")


async def schedule_backups(bot: Bot, config: Config, client: AsyncIOMotorClient):
    """Планировщик резервных копий"""
    while True:
        try:
            # Создаем и отправляем резервную копию
            await send_backup_to_admin(bot, config, client)
        except Exception as e:
            logger.error(f"Ошибка в планировщике резервных копий: {e}")
        
        # Ждем 24 часа
        await asyncio.sleep(24 * 60 * 60)