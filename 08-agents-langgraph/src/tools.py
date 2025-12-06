"""
Инструменты для ReAct агента

Инструменты - это функции, которые агент может вызывать для получения информации.
Декоратор @tool из LangChain автоматически создает описание для LLM.
"""
import json
import logging
import requests
from langchain_core.tools import tool
import rag
from config import config

logger = logging.getLogger(__name__)

@tool
def rag_search(query: str) -> str:
    """
    Ищет информацию в документах Сбербанка (условия кредитов, вкладов и других банковских продуктов).
    
    Возвращает JSON со списком источников, где каждый источник содержит:
    - source: имя файла
    - page: номер страницы (только для PDF)
    - page_content: текст документа
    """
    try:
        # Получаем релевантные документы через RAG (retrieval + reranking)
        documents = rag.retrieve_documents(query)
        
        if not documents:
            return json.dumps({"sources": []}, ensure_ascii=False)
        
        # Формируем структурированный ответ для агента
        sources = []
        for doc in documents:
            source_data = {
                "source": doc.metadata.get("source", "Unknown"),
                "page_content": doc.page_content  # Полный текст документа
            }
            # page только для PDF (у JSON документов его нет)
            if "page" in doc.metadata:
                source_data["page"] = doc.metadata["page"]
            sources.append(source_data)
        
        # ensure_ascii=False для корректной кириллицы
        return json.dumps({"sources": sources}, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error in rag_search: {e}", exc_info=True)
        return json.dumps({"sources": []}, ensure_ascii=False)


@tool
def currency_converter(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Конвертирует сумму из одной валюты в другую.
    
    Args:
        amount: Сумма для конвертации
        from_currency: Исходная валюта (USD, EUR, RUB)
        to_currency: Целевая валюта (USD, EUR, RUB)
    
    Returns:
        Строка с результатом конвертации
    """
    try:
        # Проверяем наличие API ключа
        api_key = config.EXCHANGERATE_API_KEY
        if not api_key:
            return "Ошибка: API ключ для exchangerate-api.com не настроен. Добавьте EXCHANGERATE_API_KEY в .env файл."
        
        # Нормализуем коды валют к верхнему регистру
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        # Формируем URL для API запроса
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}/{amount}"
        
        # Выполняем запрос к API
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Проверяем успешность запроса
        if data.get("result") != "success":
            error_type = data.get("error-type", "unknown")
            return f"Ошибка при конвертации валюты: {error_type}"
        
        # Получаем результат конвертации
        conversion_result = data.get("conversion_result")
        conversion_rate = data.get("conversion_rate")
        
        # Формируем читаемый ответ
        result = (
            f"{amount} {from_currency} = {conversion_result:.2f} {to_currency}\n"
            f"Курс: 1 {from_currency} = {conversion_rate:.4f} {to_currency}"
        )
        
        logger.info(f"Currency conversion: {amount} {from_currency} -> {conversion_result:.2f} {to_currency}")
        return result
        
    except requests.exceptions.Timeout:
        logger.error("Timeout while connecting to exchangerate-api.com")
        return "Ошибка: превышено время ожидания ответа от сервиса конвертации валют."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in currency_converter: {e}", exc_info=True)
        return f"Ошибка при обращении к API конвертации валют: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in currency_converter: {e}", exc_info=True)
        return f"Неожиданная ошибка при конвертации валюты: {str(e)}"

