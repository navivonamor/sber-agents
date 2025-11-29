# Руководство по индексации JSON файлов

## Что было изменено в `indexer_with_json.py`

### Проблема
Изначально использовался `JSONLoader` с `jq_schema='.[].full_text'`, который извлекал только текстовое содержимое из поля `full_text`, но **не сохранял метаданные** (категорию, вопрос, URL и т.д.).

### Решение
Заменили `JSONLoader` на ручную загрузку JSON с созданием документов LangChain, которые включают:
- **page_content**: полный текст из поля `full_text`
- **metadata**: все важные поля (url, question, category, type)

### Код изменений

```python
def load_json_documents(json_file_path: str) -> list:
    """
    Загрузка документов из JSON файла с вопросами-ответами
    Каждая пара Q&A становится отдельным чанком с метаданными
    """
    json_path = Path(json_file_path)
    if not json_path.exists():
        logger.warning(f"JSON file {json_file_path} does not exist")
        return []
    
    # Загружаем JSON вручную для лучшего контроля над метаданными
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    documents = []
    for item in data:
        # Создаем документ с полным текстом и метаданными
        doc = Document(
            page_content=item.get('full_text', ''),
            metadata={
                'source': json_path.name,
                'url': item.get('url', ''),
                'question': item.get('question', ''),
                'category': item.get('category', ''),
                'type': item.get('type', 'qa')
            }
        )
        documents.append(doc)
    
    logger.info(f"Loaded {len(documents)} Q&A pairs from JSON with metadata")
    return documents
```

## Как это работает

### 1. Структура JSON файла
```json
[
  {
    "url": "https://www.sberbank.ru/...",
    "question": "Как заказать карту?",
    "answer": "Вы можете заказать карту...",
    "category": "Вопросы о дебетовых картах",
    "type": "individual_qa",
    "full_text": "Категория: Вопросы о дебетовых картах\n\nВопрос: Как заказать карту?\n\nОтвет: Вы можете заказать карту..."
  }
]
```

### 2. Что происходит при индексации

1. **Загрузка JSON**: Файл читается целиком
2. **Создание документов**: Для каждого элемента массива создается `Document`:
   - `page_content` = `full_text` (содержит категорию, вопрос и ответ)
   - `metadata` = все остальные поля
3. **Векторизация**: Документы преобразуются в векторные представления
4. **Сохранение**: Векторы сохраняются в `InMemoryVectorStore`

### 3. Преимущества нового подхода

✅ **Сохранение метаданных**: Можно фильтровать по категории, типу и т.д.
✅ **Ссылки на источники**: URL сохраняется для каждого документа
✅ **Лучшая трассируемость**: Можно показать пользователю, откуда взят ответ
✅ **Гибкость**: Легко добавить новые поля метаданных

## Использование

### Запуск индексации
```bash
# Через бота
/reindex

# Или напрямую через Python
python -c "from src.indexer_with_json import reindex_all; import asyncio; asyncio.run(reindex_all())"
```

### Проверка результатов
После индексации вы можете задавать вопросы боту, и он будет искать ответы как в PDF, так и в JSON файлах.

Пример:
```
Пользователь: Как заказать карту?
Бот: [Находит ответ из JSON файла с метаданными]
```

## Дополнительные возможности

### Фильтрация по метаданным (будущее улучшение)
```python
# Можно добавить фильтрацию по категории
retriever = vector_store.as_retriever(
    search_kwargs={
        'k': 5,
        'filter': {'category': 'Вопросы о дебетовых картах'}
    }
)
```

### Отображение источников в ответе
В `rag.py` функция `format_chunks` уже форматирует чанки с метаданными:
```python
def format_chunks(chunks):
    formatted_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.metadata.get('source', 'Unknown')
        category = chunk.metadata.get('category', '')
        url = chunk.metadata.get('url', '')
        
        formatted_parts.append(
            f"[Источник {i}: {source}, Категория: {category}]\n{chunk.page_content}"
        )
    return "\n\n---\n\n".join(formatted_parts)
```

## Troubleshooting

### Проблема: JSON файл не найден
```
WARNING - JSON file data/sberbank_help_documents.json does not exist
```
**Решение**: Убедитесь, что файл находится в директории `data/`

### Проблема: Пустые документы
```
WARNING - No documents found to index
```
**Решение**: Проверьте, что JSON файл не пустой и имеет правильную структуру

### Проблема: Ошибка кодировки
```
UnicodeDecodeError: 'charmap' codec can't decode...
```
**Решение**: Файл открывается с `encoding='utf-8'`, это должно решить проблему
