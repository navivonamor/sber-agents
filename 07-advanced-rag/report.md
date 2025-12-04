# Отчёт о выполнении задания — Эксперименты Retrieval

Дата создания отчёта: 2025-12-04

**Краткое содержание**:
- В проекте проведены три класса экспериментов retrieval: `semantic`, `hybrid`, `hybrid_reranker`.
- Ниже приведены конфигурации, результаты RAGAS-метрик, сравнительный анализ и вывод о лучшей конфигурации для нашей задачи.

**1. Конфигурации экспериментов**

- **Semantic**:
  - Retrieval mode: `semantic`
  - Embedding provider: `huggingface`
  - Embedding model: `intfloat/multilingual-e5-base`
  - Device: `cpu`
  - LangSmith tracing: `True`
  - Show sources: `False`

- **Hybrid**:
  - Retrieval mode: `hybrid`
  - Embedding provider: `huggingface`
  - Embedding model: `intfloat/multilingual-e5-base`
  - Device: `cpu`
  - Semantic k: `10`, BM25 k: `10`
  - Ensemble weights: `0.5/0.5`
  - LangSmith tracing: `True`
  - Show sources: `False`

- **Hybrid + Reranker**:
  - Retrieval mode: `hybrid_reranker`
  - Embedding provider: `huggingface`
  - Embedding model: `intfloat/multilingual-e5-base`
  - Device: `cpu`
  - Semantic k: `10`, BM25 k: `10`
  - Ensemble weights: `0.5/0.5`
  - Cross-encoder: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
  - Reranker top-k: `3`
  - LangSmith tracing: `True`
  - Show sources: `False`

**2. Таблица RAGAS-метрик**

| Метрика / Эксперимент | semantic | hybrid | hybrid_reranker |
|---|---:|---:|---:|
| faithfulness | 0.774 | 0.663 | 0.791 |
| answer_relevancy | 0.760 | 0.751 | 0.746 |
| answer_correctness | 0.631 | 0.575 | 0.659 |
| answer_similarity | 0.912 | 0.916 | 0.912 |
| context_recall | 1.000 | 0.907 | 0.833 |
| context_precision | 0.709 | 0.539 | 0.889 |

**Примечание**: для каждого эксперимента использовался датасет из 6 примеров.

**3. Сравнительный анализ результатов**

- Общая картина:
  - `hybrid` показал наихудшие значения по большинству метрик (особенно `faithfulness` и `answer_correctness`).
  - `semantic` и `hybrid_reranker` демонстрируют лучшие результаты в разных метриках.

- Faithfulness (насколько ответ верно отражает контекст):
  - Лучший результат у `hybrid_reranker` (0.791), второй `semantic` (0.774), худший `hybrid` (0.663).
  - Возможная интерпретация: reranker помогает выбрать более релевантные и содержательно точные фрагменты контекста, что повышает faithfulness.

- Answer correctness (правильность ответа):
  - Лучший у `hybrid_reranker` (0.659), затем `semantic` (0.631), затем `hybrid` (0.575).
  - Комбинация гибридного поиска с перекодировщиком (cross-encoder) улучшает точность ответов по сравнению с чисто семантическим или гибридным без reranker.

- Answer relevancy и similarity:
  - `answer_relevancy` у `semantic` (0.760) чуть выше, чем у `hybrid_reranker` (0.746), `hybrid` близок (0.751).
  - `answer_similarity` высока и стабильна во всех трёх (≈0.912–0.916), что указывает на высокое соответствие генерируемых ответов по содержанию.

- Context recall vs context precision:
  - `semantic` имеет максимальный `context_recall` (1.000) — то есть семантический поиск нашёл почти все релевантные куски контекста, но precision у него ниже (0.709), чем у reranker-конфигурации.
  - `hybrid_reranker` даёт лучшую `context_precision` (0.889) при несколько меньшем `context_recall` (0.833) — это означает, что reranker сокращает шум и поднимает качество верхней части списка (меньше нерелевантных фрагментов среди тех, что используются для генерации ответа).
  - `hybrid` является компромиссом по recall/precision, но с относительно низкой precision и средней recall.

- Почему такие различия:
  - Семантический поиск возвращает набор фрагментов, хорошо охватывающих релевантный контент (высокий recall), но среди возвращаемых фрагментов может быть больше нерелевантных или менее точных (ниже precision).
  - Гибридный поиск без reranker объединяет сигналы BM25 + семантики; это может дать более разнородный набор результатов и в данном случае привело к ухудшению correctness и faithfulness.
  - Добавление cross-encoder (reranker) улучшает ранжирование и повышает precision верхних результатов, что положительно сказывается на faithfulness и correctness.

**4. Выводы**

- Какая конфигурация оказалась лучшей для нашей задачи:
  - По совокупности ключевых метрик `faithfulness` и `answer_correctness` лучшей конфигурацией является `hybrid_reranker` (гибридный поиск с cross-encoder reranker).
  - Если важен максимальный охват источников (context recall) — `semantic` даёт наивысший recall (1.000), что может быть полезно при задачах, где критично не пропустить релевантную информацию. Однако высокая recall при более низкой precision может привести к включению нерелевантного контекста в ответы.

- Конкретная рекомендация для нашей задачи:
  - Если приоритет — корректность и достоверность ответов (minimize hallucination) — используйте `hybrid_reranker` с выбранным `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` и `reranker top-k = 3`.
  - Если нужен максимальный охват сведений (например, для дальнейшего ручного анализа источников) — `semantic` с высокими `k`-значениями может быть предпочтителен.

**5. Скриншоты (ссылки на файлы в репозитории)**

- [Эксперимент 1 — semantic (скриншот)](screenshots/experiment-1-semantic-baseline.png)
- [Эксперимент 2 — hybrid (скриншот)](screenshots/experiment-2-hybrid.png)
- [Эксперимент 3 — hybrid + reranker (скриншот)](screenshots/experiment-3-hybrid-reranker.png)

(Файлы находятся в `screenshots/`)