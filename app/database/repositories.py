from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.database.models import User, Product, ProductItem, Category, Transaction, Promo, Settings


class BaseRepository:
    """Базовый класс для репозиториев"""
    
    def __init__(self, db: AsyncIOMotorDatabase = None):
        self.db = db
    
    def set_db(self, db: AsyncIOMotorDatabase):
        """Установить соединение с базой данных"""
        self.db = db


class UserRepository(BaseRepository):
    """Репозиторий для работы с пользователями"""
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        user_data = await self.db.users.find_one({"user_id": user_id})
        if user_data:
            return User(**user_data)
        return None
    
    async def get_or_create_user(self, user_id: int, username: str = None, 
                                first_name: str = None, last_name: str = None) -> User:
        """Получить пользователя или создать нового"""
        user = await self.get_user(user_id)
        if not user:
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                balance=0.0,
                purchases=0,
                is_admin=False,
                created_at=datetime.now(),
                last_active=datetime.now()
            )
            await self.db.users.insert_one(user.model_dump(by_alias=True))
        else:
            # Обновляем время последней активности
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"last_active": datetime.now()}}
            )
            user.last_active = datetime.now()
        return user
    
    async def update_user(self, user: User) -> bool:
        """Обновить информацию о пользователе"""
        result = await self.db.users.update_one(
            {"user_id": user.user_id},
            {"$set": user.model_dump(exclude={"id"}, by_alias=True)}
        )
        return result.modified_count > 0
    
    async def update_balance(self, user_id: int, amount: float) -> bool:
        """Обновить баланс пользователя"""
        result = await self.db.users.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": amount}}
        )
        return result.modified_count > 0
    
    async def increment_purchases(self, user_id: int, count: int = 1) -> bool:
        """Увеличить количество покупок пользователя"""
        result = await self.db.users.update_one(
            {"user_id": user_id},
            {"$inc": {"purchases": count}}
        )
        return result.modified_count > 0
    
    async def get_all_users(self, limit: int = 100, skip: int = 0) -> List[User]:
        """Получить список всех пользователей"""
        users_data = await self.db.users.find().skip(skip).limit(limit).to_list(length=limit)
        return [User(**user) for user in users_data]
    
    async def count_users(self) -> int:
        """Получить количество пользователей"""
        return await self.db.users.count_documents({})


class CategoryRepository(BaseRepository):
    """Репозиторий для работы с категориями товаров"""
    
    async def get_category(self, category_id: Union[str, ObjectId]) -> Optional[Category]:
        """Получить категорию по ID"""
        if isinstance(category_id, str):
            category_id = ObjectId(category_id)
        
        category_data = await self.db.categories.find_one({"_id": category_id})
        if category_data:
            return Category(**category_data)
        return None
    
    async def get_all_categories(self) -> List[Category]:
        """Получить все категории"""
        categories_data = await self.db.categories.find().to_list(length=100)
        return [Category(**category) for category in categories_data]
    
    async def create_category(self, name: str, description: str = None) -> Category:
        """Создать новую категорию"""
        category = Category(
            name=name,
            description=description,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        result = await self.db.categories.insert_one(category.model_dump(by_alias=True))
        category.id = result.inserted_id
        return category
    
    async def update_category(self, category: Category) -> bool:
        """Обновить категорию"""
        category.updated_at = datetime.now()
        result = await self.db.categories.update_one(
            {"_id": category.id},
            {"$set": category.model_dump(exclude={"id"}, by_alias=True)}
        )
        return result.modified_count > 0
    
    async def delete_category(self, category_id: Union[str, ObjectId]) -> bool:
        """Удалить категорию"""
        if isinstance(category_id, str):
            category_id = ObjectId(category_id)
        
        result = await self.db.categories.delete_one({"_id": category_id})
        return result.deleted_count > 0


class ProductRepository(BaseRepository):
    """Репозиторий для работы с товарами"""
    
    async def get_product(self, product_id: Union[str, ObjectId]) -> Optional[Product]:
        """Получить товар по ID"""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        product_data = await self.db.products.find_one({"_id": product_id})
        if product_data:
            return Product(**product_data)
        return None
    
    async def get_all_products(self, available_only: bool = False, 
                              category_id: Union[str, ObjectId] = None,
                              limit: int = 100, skip: int = 0) -> List[Product]:
        """Получить все товары"""
        query = {}
        
        if available_only:
            query["quantity"] = {"$gt": 0}
        
        if category_id:
            if isinstance(category_id, str):
                category_id = ObjectId(category_id)
            query["category_id"] = category_id
        
        products_data = await self.db.products.find(query).skip(skip).limit(limit).to_list(length=limit)
        return [Product(**product) for product in products_data]
    
    async def get_popular_products(self, limit: int = 5) -> List[Product]:
        """Получить популярные товары"""
        products_data = await self.db.products.find(
            {"quantity": {"$gt": 0}}
        ).sort("sales_count", -1).limit(limit).to_list(length=limit)
        return [Product(**product) for product in products_data]
    
    async def create_product(self, name: str, price: float, description: str = None,
                            category_id: Union[str, ObjectId] = None, quantity: int = 0,
                            image_url: str = None, instruction_link: str = None,
                            stars_enabled: bool = False, stars_price: int | None = None) -> Product:
        """Создать новый товар"""
        if category_id and isinstance(category_id, str):
            category_id = ObjectId(category_id)
        
        product = Product(
            name=name,
            description=description,
            price=price,
            category_id=category_id,
            quantity=quantity,
            image_url=image_url,
            instruction_link=instruction_link,
            stars_enabled=stars_enabled,
            stars_price=stars_price,
            sales_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        result = await self.db.products.insert_one(product.model_dump(by_alias=True))
        product.id = result.inserted_id
        return product
    
    async def update_product(self, product: Product) -> bool:
        """Обновить товар"""
        product.updated_at = datetime.now()
        result = await self.db.products.update_one(
            {"_id": product.id},
            {"$set": product.model_dump(exclude={"id"}, by_alias=True)}
        )
        return result.modified_count > 0
    
    async def delete_product(self, product_id: Union[str, ObjectId]) -> bool:
        """Удалить товар"""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        result = await self.db.products.delete_one({"_id": product_id})
        return result.deleted_count > 0
    
    async def update_quantity(self, product_id: Union[str, ObjectId], quantity_change: int) -> bool:
        """Изменить количество товара"""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        result = await self.db.products.update_one(
            {"_id": product_id},
            {"$inc": {"quantity": quantity_change}}
        )
        return result.modified_count > 0
    
    async def increment_sales(self, product_id: Union[str, ObjectId], count: int = 1) -> bool:
        """Увеличить счетчик продаж товара"""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        result = await self.db.products.update_one(
            {"_id": product_id},
            {"$inc": {"sales_count": count}}
        )
        return result.modified_count > 0


class TransactionRepository(BaseRepository):
    """Репозиторий для работы с транзакциями"""
    
    async def get_transaction(self, transaction_id: Union[str, ObjectId]) -> Optional[Transaction]:
        """Получить транзакцию по ID"""
        if isinstance(transaction_id, str):
            transaction_id = ObjectId(transaction_id)
        
        transaction_data = await self.db.transactions.find_one({"_id": transaction_id})
        if transaction_data:
            return Transaction(**transaction_data)
        return None
    
    async def get_transaction_by_payment_id(self, payment_id: str) -> Optional[Transaction]:
        """Получить транзакцию по ID платежа"""
        transaction_data = await self.db.transactions.find_one({"payment_id": payment_id})
        if transaction_data:
            return Transaction(**transaction_data)
        return None
    
    async def get_transaction_by_receipt(self, receipt_id: str) -> Optional[Transaction]:
        """Получить транзакцию по номеру чека"""
        transaction_data = await self.db.transactions.find_one({"receipt_id": receipt_id})
        if transaction_data:
            return Transaction(**transaction_data)
        return None
    
    async def get_user_transactions(self, user_id: int, 
                                  transaction_type: str = None,
                                  limit: int = 10, skip: int = 0) -> List[Transaction]:
        """Получить транзакции пользователя"""
        query = {"user_id": user_id}
        
        if transaction_type:
            query["type"] = transaction_type
        
        transactions_data = await self.db.transactions.find(query).sort(
            "created_at", -1
        ).skip(skip).limit(limit).to_list(length=limit)
        
        return [Transaction(**tx) for tx in transactions_data]
    
    async def create_transaction(self, user_id: int, amount: float, 
                               transaction_type: str, status: str = "pending",
                               payment_method: str = None, payment_id: str = None,
                               product_id: Union[str, ObjectId] = None,
                               receipt_id: str = None,
                               expires_at: datetime = None) -> Transaction:
        """Создать новую транзакцию"""
        if product_id and isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            type=transaction_type,
            status=status,
            payment_method=payment_method,
            payment_id=payment_id,
            product_id=product_id,
            receipt_id=receipt_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            expires_at=expires_at
        )
        
        result = await self.db.transactions.insert_one(transaction.model_dump(by_alias=True))
        transaction.id = result.inserted_id
        return transaction
    
    async def update_transaction(self, transaction: Transaction) -> bool:
        """Обновить транзакцию"""
        transaction.updated_at = datetime.now()
        result = await self.db.transactions.update_one(
            {"_id": transaction.id},
            {"$set": transaction.model_dump(exclude={"id"}, by_alias=True)}
        )
        return result.modified_count > 0
    
    async def update_transaction_status(self, transaction_id: Union[str, ObjectId], 
                                      status: str) -> bool:
        """Обновить статус транзакции"""
        if isinstance(transaction_id, str):
            transaction_id = ObjectId(transaction_id)
        
        result = await self.db.transactions.update_one(
            {"_id": transaction_id},
            {"$set": {"status": status, "updated_at": datetime.now()}}
        )
        return result.modified_count > 0
    
    async def get_statistics_by_period(self, days: int) -> dict:
        """Получить статистику за период"""
        from datetime import datetime, timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Статистика по транзакциям
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": start_date, "$lte": end_date},
                    "status": "completed"
                }
            },
            {
                "$group": {
                    "_id": "$type",
                    "count": {"$sum": 1},
                    "total_amount": {"$sum": "$amount"}
                }
            }
        ]
        
        result = await self.db.transactions.aggregate(pipeline).to_list(None)
        
        stats = {
            "purchases": {"count": 0, "amount": 0},
            "deposit": {"count": 0, "amount": 0}
        }
        
        for item in result:
            if item["_id"] == "purchase":
                stats["purchases"]["count"] = item["count"]
                stats["purchases"]["amount"] = item["total_amount"]
            elif item["_id"] == "deposit":
                stats["deposit"]["count"] = item["count"]
                stats["deposit"]["amount"] = item["total_amount"]
        
        return stats

    async def get_popular_products_stats(self, limit: int = 5) -> List[dict]:
        """Получить статистику популярных товаров"""
        pipeline = [
            {
                "$match": {
                    "type": "purchase",
                    "status": "completed"
                }
            },
            {
                "$group": {
                    "_id": "$product_id",
                    "purchase_count": {"$sum": 1},
                    "total_amount": {"$sum": "$amount"}
                }
            },
            {
                "$sort": {"purchase_count": -1}
            },
            {
                "$limit": limit
            }
        ]
        
        return await self.db.transactions.aggregate(pipeline).to_list(None)
    
    async def get_stats(self, transaction_type: str = None, 
                       start_date: datetime = None, 
                       end_date: datetime = None) -> Dict[str, Any]:
        """Получить статистику по транзакциям"""
        query = {}
        
        if transaction_type:
            query["type"] = transaction_type
        
        if start_date or end_date:
            query["created_at"] = {}
            
            if start_date:
                query["created_at"]["$gte"] = start_date
            
            if end_date:
                query["created_at"]["$lte"] = end_date
        
        # Только завершенные транзакции
        query["status"] = "completed"
        
        # Получаем количество и сумму транзакций
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": None,
                "count": {"$sum": 1},
                "total_amount": {"$sum": "$amount"}
            }}
        ]
        
        result = await self.db.transactions.aggregate(pipeline).to_list(length=1)
        
        if result:
            return {
                "count": result[0]["count"],
                "total_amount": result[0]["total_amount"]
            }
        
        return {"count": 0, "total_amount": 0.0}


class PromoRepository(BaseRepository):
    """Репозиторий для работы с промокодами"""
    
    async def get_promo(self, promo_id: Union[str, ObjectId]) -> Optional[Promo]:
        """Получить промокод по ID"""
        if isinstance(promo_id, str):
            promo_id = ObjectId(promo_id)
        
        promo_data = await self.db.promos.find_one({"_id": promo_id})
        if promo_data:
            return Promo(**promo_data)
        return None
    
    async def get_promo_by_code(self, code: str) -> Optional[Promo]:
        """Получить промокод по коду"""
        promo_data = await self.db.promos.find_one({"code": code})
        if promo_data:
            return Promo(**promo_data)
        return None
    
    async def get_all_promos(self, active_only: bool = False) -> List[Promo]:
        """Получить все промокоды"""
        query = {}
        
        if active_only:
            now = datetime.now()
            query["$and"] = [
                {"$or": [
                    {"expires_at": {"$gt": now}},
                    {"expires_at": None}
                ]},
                {"$or": [
                    {"used_count": {"$lt": "$max_uses"}},
                    {"max_uses": 0}
                ]}
            ]
        
        promos_data = await self.db.promos.find(query).to_list(length=100)
        return [Promo(**promo) for promo in promos_data]
    
    async def create_promo(self, code: str, discount_percent: float, 
                         max_uses: int = 0, product_id: Union[str, ObjectId] = None,
                         expires_at: datetime = None) -> Promo:
        """Создать новый промокод"""
        if product_id and isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        promo = Promo(
            code=code,
            discount_percent=discount_percent,
            max_uses=max_uses,
            used_count=0,
            product_id=product_id,
            expires_at=expires_at,
            created_at=datetime.now()
        )
        
        result = await self.db.promos.insert_one(promo.model_dump(by_alias=True))
        promo.id = result.inserted_id
        return promo
    
    async def update_promo(self, promo: Promo) -> bool:
        """Обновить промокод"""
        result = await self.db.promos.update_one(
            {"_id": promo.id},
            {"$set": promo.model_dump(exclude={"id"}, by_alias=True)}
        )
        return result.modified_count > 0
    
    async def delete_promo(self, promo_id: Union[str, ObjectId]) -> bool:
        """Удалить промокод"""
        if isinstance(promo_id, str):
            promo_id = ObjectId(promo_id)
        
        result = await self.db.promos.delete_one({"_id": promo_id})
        return result.deleted_count > 0
    
    async def increment_usage(self, promo_id: Union[str, ObjectId]) -> bool:
        """Увеличить счетчик использований промокода"""
        if isinstance(promo_id, str):
            promo_id = ObjectId(promo_id)
        
        result = await self.db.promos.update_one(
            {"_id": promo_id},
            {"$inc": {"used_count": 1}}
        )
        return result.modified_count > 0
    
    async def is_promo_valid(self, code: str, product_id: Union[str, ObjectId] = None) -> bool:
        """Проверить, действителен ли промокод"""
        promo = await self.get_promo_by_code(code)
        
        if not promo:
            return False
        
        now = datetime.now()
        
        # Проверяем срок действия
        if promo.expires_at and promo.expires_at < now:
            return False
        
        # Проверяем количество использований
        if promo.max_uses > 0 and promo.used_count >= promo.max_uses:
            return False
        
        # Проверяем, подходит ли промокод для данного товара
        if promo.product_id and product_id:
            if isinstance(product_id, str):
                product_id = ObjectId(product_id)
            
            if promo.product_id != product_id:
                return False
        
        return True


class SettingsRepository(BaseRepository):
    """Репозиторий для работы с настройками"""
    
    async def get_setting(self, key: str) -> Any:
        """Получить значение настройки по ключу"""
        setting_data = await self.db.settings.find_one({"key": key})
        if setting_data:
            return setting_data["value"]
        return None
    
    async def set_setting(self, key: str, value: Any) -> bool:
        """Установить значение настройки"""
        result = await self.db.settings.update_one(
            {"key": key},
            {"$set": {"value": value, "updated_at": datetime.now()}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    
    async def delete_setting(self, key: str) -> bool:
        """Удалить настройку"""
        result = await self.db.settings.delete_one({"key": key})
        return result.deleted_count > 0


class ProductItemRepository(BaseRepository):
    """Репозиторий для работы с позициями товаров"""
    
    async def get_item(self, item_id: Union[str, ObjectId]) -> Optional[ProductItem]:
        """Получить позицию товара по ID"""
        if isinstance(item_id, str):
            item_id = ObjectId(item_id)
        
        item_data = await self.db.product_items.find_one({"_id": item_id})
        if item_data:
            return ProductItem(**item_data)
        return None
    
    async def get_available_items(self, product_id: Union[str, ObjectId], limit: int = 1) -> List[ProductItem]:
        """Получить доступные позиции товара"""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        items_data = await self.db.product_items.find({
            "product_id": product_id,
            "is_sold": False
        }).limit(limit).to_list(length=limit)
        
        return [ProductItem(**item) for item in items_data]
    
    async def get_all_items(self, product_id: Union[str, ObjectId]) -> List[ProductItem]:
        """Получить все позиции товара"""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        items_data = await self.db.product_items.find({"product_id": product_id}).to_list(length=1000)
        return [ProductItem(**item) for item in items_data]
    
    async def create_item(self, product_id: Union[str, ObjectId], data: str) -> ProductItem:
        """Создать новую позицию товара"""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        item = ProductItem(
            product_id=product_id,
            data=data,
            is_sold=False,
            created_at=datetime.now()
        )
        
        result = await self.db.product_items.insert_one(item.model_dump(by_alias=True))
        item.id = result.inserted_id
        return item
    
    async def create_multiple_items(self, product_id: Union[str, ObjectId], items_data: List[str]) -> List[ProductItem]:
        """Создать несколько позиций товара"""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        items = []
        for data in items_data:
            item = ProductItem(
                product_id=product_id,
                data=data.strip(),
                is_sold=False,
                created_at=datetime.now()
            )
            items.append(item.model_dump(by_alias=True))
        
        if items:
            result = await self.db.product_items.insert_many(items)
            # Получаем созданные элементы
            created_items = await self.db.product_items.find({
                "_id": {"$in": result.inserted_ids}
            }).to_list(length=len(items))
            
            return [ProductItem(**item) for item in created_items]
        return []
    
    async def mark_as_sold(self, item_id: Union[str, ObjectId], user_id: int, receipt_id: str | None = None) -> bool:
        """Отметить позицию как проданную"""
        if isinstance(item_id, str):
            item_id = ObjectId(item_id)
        
        result = await self.db.product_items.update_one(
            {"_id": item_id},
            {
                "$set": {
                    "is_sold": True,
                    "sold_at": datetime.now(),
                    "sold_to_user_id": user_id,
                    **({"receipt_id": receipt_id} if receipt_id else {})
                }
            }
        )
        return result.modified_count > 0
    
    async def delete_item(self, item_id: Union[str, ObjectId]) -> bool:
        """Удалить позицию товара"""
        if isinstance(item_id, str):
            item_id = ObjectId(item_id)
        
        result = await self.db.product_items.delete_one({"_id": item_id})
        return result.deleted_count > 0
    
    async def get_items_by_receipt(self, receipt_id: str, user_id: int | None = None) -> List[ProductItem]:
        """Получить проданные позиции по номеру чека (и, опционально, по пользователю)"""
        query: Dict[str, Any] = {"receipt_id": receipt_id}
        if user_id is not None:
            query["sold_to_user_id"] = user_id
        items_data = await self.db.product_items.find(query).to_list(length=100)
        return [ProductItem(**item) for item in items_data]

    async def count_available_items(self, product_id: Union[str, ObjectId]) -> int:
        """Подсчитать количество доступных позиций товара"""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        return await self.db.product_items.count_documents({
            "product_id": product_id,
            "is_sold": False
        })
    
    async def count_total_items(self, product_id: Union[str, ObjectId]) -> int:
        """Подсчитать общее количество позиций товара"""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        return await self.db.product_items.count_documents({"product_id": product_id})
    
    async def update_product_quantity_from_items(self, product_id: Union[str, ObjectId]) -> bool:
        """Обновить количество товара на основе доступных позиций"""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        # Подсчитываем количество доступных позиций
        available_count = await self.count_available_items(product_id)
        
        # Обновляем количество товара
        result = await self.db.products.update_one(
            {"_id": product_id},
            {"$set": {"quantity": available_count}}
        )
        
        return result.modified_count > 0
    
    async def delete_items_by_product(self, product_id: Union[str, ObjectId]) -> int:
        """Удалить все позиции товара"""
        if isinstance(product_id, str):
            product_id = ObjectId(product_id)
        
        result = await self.db.product_items.delete_many({"product_id": product_id})
        return result.deleted_count