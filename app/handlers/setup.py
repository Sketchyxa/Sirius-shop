from aiogram import Dispatcher
from loguru import logger

from app.handlers import user, admin, buy, deposit, search, broadcast, products, admin_panel, product_image, balance


async def setup_all_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    # Регистрация обработчиков пользователя
    dp.include_router(user.router)
    logger.debug("Зарегистрированы обработчики пользователя")
    
    # Регистрация обработчиков админ-панели
    dp.include_router(admin_panel.router)
    logger.debug("Зарегистрированы обработчики админ-панели")
    
    # Регистрация обработчиков администратора
    dp.include_router(admin.router)
    logger.debug("Зарегистрированы обработчики администратора")
    
    # Регистрация обработчиков покупки
    dp.include_router(buy.router)
    logger.debug("Зарегистрированы обработчики покупки")
    
    # Регистрация обработчиков управления товарами
    dp.include_router(products.router)
    logger.debug("Зарегистрированы обработчики управления товарами")
    
    # Регистрация обработчиков поиска
    dp.include_router(search.router)
    logger.debug("Зарегистрированы обработчики поиска")
    
    # Регистрация обработчиков рассылки
    dp.include_router(broadcast.router)
    logger.debug("Зарегистрированы обработчики рассылки")
    
    # Регистрация обработчиков управления балансом (высокий приоритет)
    dp.include_router(balance.router)
    logger.debug("Зарегистрированы обработчики управления балансом")
    
    # Регистрация обработчиков пополнения
    dp.include_router(deposit.router)
    logger.debug("Зарегистрированы обработчики пополнения")
    
    # Регистрация обработчиков загрузки изображений товаров
    dp.include_router(product_image.router)
    logger.debug("Зарегистрированы обработчики загрузки изображений товаров")
    
    logger.info("Все обработчики зарегистрированы")