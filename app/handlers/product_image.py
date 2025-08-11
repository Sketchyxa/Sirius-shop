from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger
from bson import ObjectId

from app.filters.admin import AdminFilter
from app.states.admin_states import ProductManagement
from app.database.repositories import ProductRepository
from app.keyboards import get_admin_product_actions_keyboard


router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.callback_query(F.data.startswith("admin:upload_product_image:"))
async def upload_product_image(callback: CallbackQuery, state: FSMContext, product_repo: ProductRepository):
    """Загрузка изображения для товара"""
    # Получаем ID товара
    product_id = callback.data.split(":")[-1]
    
    # Сохраняем ID товара в состоянии
    await state.update_data(product_id=product_id)
    
    # Получаем товар
    product = await product_repo.get_product(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    # Переходим к состоянию загрузки изображения
    await state.set_state(ProductManagement.upload_image)
    
    await callback.message.edit_text(
        f"🖼 <b>Загрузка изображения для товара</b>\n\n"
        f"Товар: <b>{product.name}</b>\n\n"
        "Отправьте изображение для товара.\n"
        "Для отмены нажмите /cancel"
    )
    
    await callback.answer()


@router.message(ProductManagement.upload_image, F.photo)
async def process_product_image(message: Message, state: FSMContext, product_repo: ProductRepository):
    """Обработка загруженного изображения товара"""
    # Получаем данные из состояния
    data = await state.get_data()
    product_id = data.get("product_id")
    
    if not product_id:
        await message.answer("❌ Ошибка: не найден ID товара")
        await state.clear()
        return
    
    # Получаем товар
    product = await product_repo.get_product(product_id)
    
    if not product:
        await message.answer("❌ Товар не найден")
        await state.clear()
        return
    
    try:
        # Получаем файл с наилучшим качеством
        photo = message.photo[-1]
        file_id = photo.file_id
        
        # Обновляем товар с новым file_id
        product.image_url = file_id
        await product_repo.update_product(product)
        
        # Отправляем сообщение об успешной загрузке
        await message.answer_photo(
            photo=file_id,
            caption=f"✅ <b>Изображение для товара успешно загружено</b>\n\n"
                   f"Товар: <b>{product.name}</b>",
            reply_markup=get_admin_product_actions_keyboard(str(product.id))
        )
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке изображения товара: {e}")
        await message.answer(
            "❌ <b>Произошла ошибка при загрузке изображения</b>\n\n"
            "Попробуйте еще раз позже или обратитесь к разработчику."
        )
        await state.clear()


@router.message(ProductManagement.upload_image)
async def invalid_product_image(message: Message, state: FSMContext):
    """Обработка неверного формата изображения"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Загрузка изображения отменена")
        return
    
    await message.answer(
        "❌ <b>Неверный формат</b>\n\n"
        "Пожалуйста, отправьте изображение (фото).\n"
        "Для отмены нажмите /cancel"
    )