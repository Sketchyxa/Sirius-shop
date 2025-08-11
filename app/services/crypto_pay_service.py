import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List, Union
from loguru import logger


class CryptoPayService:
    """Сервис для работы с Crypto Pay API"""
    
    def __init__(self, api_token: str, testnet: bool = False):
        """
        Инициализация сервиса
        
        Args:
            api_token: Токен API Crypto Pay
            testnet: Использовать тестовую сеть
        """
        self.api_token = api_token
        self.base_url = "https://testnet-pay.crypt.bot/api" if testnet else "https://pay.crypt.bot/api"
        self.headers = {
            "Crypto-Pay-API-Token": api_token,
            "Content-Type": "application/json"
        }
        self.testnet = testnet
        logger.debug(f"Инициализирован CryptoPayService. Testnet: {testnet}")
    
    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Выполнение запроса к API
        
        Args:
            method: HTTP метод (GET, POST)
            endpoint: Конечная точка API
            params: Параметры запроса
            
        Returns:
            Dict[str, Any]: Ответ API
        """
        url = f"{self.base_url}/{endpoint}"
        logger.debug(f"Запрос к Crypto Pay API: {method} {url}")
        
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # до 3 попыток при сетевых ошибках/5xx
                attempts = 3
                last_exc = None
                for i in range(attempts):
                    try:
                        if method == "GET":
                            async with session.get(url, headers=self.headers, params=params) as response:
                                data = await response.json()
                        elif method == "POST":
                            async with session.post(url, headers=self.headers, json=params) as response:
                                data = await response.json()
                        else:
                            raise ValueError(f"Неподдерживаемый HTTP метод: {method}")

                        if not data.get("ok"):
                            error_details = data.get("error", {})
                            logger.error(f"Ошибка API Crypto Pay: {error_details}")
                            # 5xx — повтор, иначе — сразу ошибка
                            if isinstance(error_details, dict) and str(error_details.get("code")).startswith("5") and i < attempts - 1:
                                await asyncio.sleep(1 * (i + 1))
                                continue
                            raise Exception(f"Ошибка API Crypto Pay: {error_details}")

                        logger.debug(f"Успешный ответ от Crypto Pay API: {endpoint}")
                        return data.get("result", {})
                    except aiohttp.ClientError as e:
                        last_exc = e
                        logger.warning(f"Сетевая ошибка Crypto Pay (попытка {i+1}/{attempts}): {e}")
                        if i < attempts - 1:
                            await asyncio.sleep(1 * (i + 1))
                            continue
                        raise
                if last_exc:
                    raise last_exc
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при запросе к Crypto Pay API: {e}")
            raise Exception(f"Ошибка сети при запросе к Crypto Pay API: {e}")
        except Exception as e:
            logger.error(f"Ошибка запроса к Crypto Pay API: {e}")
            raise
    
    async def get_me(self) -> Dict[str, Any]:
        """
        Получение информации о приложении
        
        Returns:
            Dict[str, Any]: Информация о приложении
        """
        logger.info(f"Запрос информации о приложении Crypto Pay. Testnet: {self.testnet}")
        return await self._make_request("GET", "getMe")
    
    async def create_invoice(
        self,
        amount: Union[float, str],
        asset: str = "USDT",
        description: Optional[str] = None,
        hidden_message: Optional[str] = None,
        payload: Optional[str] = None,
        allow_comments: bool = True,
        allow_anonymous: bool = True,
        expires_in: Optional[int] = None,
        fiat: Optional[str] = None,
        currency_type: str = "crypto",
        accepted_assets: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Создание счета на оплату
        
        Args:
            amount: Сумма счета
            asset: Криптовалюта (USDT, TON, BTC и т.д.)
            description: Описание счета
            hidden_message: Скрытое сообщение
            payload: Полезная нагрузка
            allow_comments: Разрешить комментарии
            allow_anonymous: Разрешить анонимную оплату
            expires_in: Время жизни счета в секундах
            fiat: Фиатная валюта (USD, EUR, RUB и т.д.)
            currency_type: Тип валюты (crypto, fiat)
            accepted_assets: Список принимаемых криптовалют
            
        Returns:
            Dict[str, Any]: Информация о созданном счете
        """
        params = {
            "amount": str(amount),
            "allow_comments": allow_comments,
            "allow_anonymous": allow_anonymous,
        }
        
        # Добавляем параметры в зависимости от типа валюты
        if currency_type == "crypto":
            params["asset"] = asset
        elif currency_type == "fiat":
            params["fiat"] = fiat
            if accepted_assets:
                params["accepted_assets"] = ",".join(accepted_assets)
        
        params["currency_type"] = currency_type
        
        # Добавляем опциональные параметры
        if description:
            params["description"] = description
        if hidden_message:
            params["hidden_message"] = hidden_message
        if payload:
            params["payload"] = payload
        if expires_in:
            params["expires_in"] = expires_in
        
        logger.info(f"Создание счета на оплату: {amount} {asset if currency_type == 'crypto' else fiat}")
        return await self._make_request("POST", "createInvoice", params)
    
    async def get_invoices(
        self,
        asset: Optional[str] = None,
        invoice_ids: Optional[List[str]] = None,
        status: Optional[str] = None,
        offset: int = 0,
        count: int = 100
    ) -> Dict[str, Any]:
        """
        Получение списка счетов
        
        Args:
            asset: Фильтр по криптовалюте
            invoice_ids: Фильтр по ID счетов
            status: Фильтр по статусу (active, paid, expired)
            offset: Смещение
            count: Количество
            
        Returns:
            Dict[str, Any]: Список счетов
        """
        params = {
            "offset": offset,
            "count": count
        }
        
        if asset:
            params["asset"] = asset
        if invoice_ids:
            params["invoice_ids"] = ",".join(invoice_ids)
        if status:
            params["status"] = status
        
        logger.info(f"Запрос списка счетов. Invoice IDs: {invoice_ids}")
        return await self._make_request("GET", "getInvoices", params)
    
    async def get_balance(self) -> List[Dict[str, Any]]:
        """
        Получение баланса
        
        Returns:
            List[Dict[str, Any]]: Список балансов по разным криптовалютам
        """
        logger.info("Запрос баланса Crypto Pay")
        return await self._make_request("GET", "getBalance")
    
    async def get_exchange_rates(self) -> List[Dict[str, Any]]:
        """
        Получение курсов обмена
        
        Returns:
            List[Dict[str, Any]]: Список курсов обмена
        """
        logger.info("Запрос курсов обмена Crypto Pay")
        return await self._make_request("GET", "getExchangeRates")
    
    async def get_currencies(self) -> Dict[str, Any]:
        """
        Получение списка поддерживаемых валют
        
        Returns:
            Dict[str, Any]: Список поддерживаемых валют
        """
        logger.info("Запрос списка поддерживаемых валют Crypto Pay")
        return await self._make_request("GET", "getCurrencies")