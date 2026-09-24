# MedExplainer 🏥🔍

**MedExplainer** — это сервис для поиска и упрощения медицинских научных исследований из **PubMed** и других доказательных источников. Он помогает пользователям находить актуальные исследования и понимать их без специальной медицинской подготовки.

---

## 🚀 Возможности

- ✅ **Поиск в PubMed** — находит исследования по запросу
- ✅ **Фильтрация по типу исследований** — только мета-анализы, РКИ, систематические обзоры и др.
- ✅ **Упрощение текста** — переводит сложные медицинские термины в простой язык
- ✅ **Оценка достоверности** — показывает уровень доказательности (высокий, средний, низкий)
- ✅ **Многоязычная поддержка** — английский и русский
- ✅ **API для интеграции** — REST API для подключения к другим сервисам
- ✅ **Веб-интерфейс** — удобный интерфейс для поиска

---

## 📦 Установка

### 1. Клонирование репозитория

```bash
cd medexplainer
git clone https://github.com/smmisha/project-zero.git
cd project-zero/medexplainer
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Отредактируйте `.env` при необходимости:

```env
# Email для PubMed API (обязательно)
PUBMED_EMAIL=your_email@example.com

# Redis для кэширования (опционально)
REDIS_URL=redis://localhost:6379/0

# Настройки FastAPI
APP_HOST=0.0.0.0
APP_PORT=8000
```

### 4. Запуск сервиса

```bash
python -m app.main
```

Или с помощью Uvicorn:

```bash
uvicorn app.main:app --reload
```

Сервис будет доступен по адресу: **http://localhost:8000**

---

## 🌐 Использование

### Веб-интерфейс

Откройте в браузере: **http://localhost:8000/static/index.html**

1. Введите запрос (например: `vitamin D depression`)
2. Выберите типы исследований (по умолчанию: мета-анализы и РКИ)
3. Укажите минимальное количество участников (опционально)
4. Выберите год публикации (опционально)
5. Выберите язык (английский или русский)
6. Нажмите **Search**

### API

#### Поиск исследований

**POST /search**

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "vitamin D depression",
    "study_types": ["meta_analysis", "randomized_controlled_trial"],
    "min_participants": 100,
    "publication_year": 2023,
    "language": "ru",
    "limit": 10
  }'
```

**GET /search**

```bash
curl "http://localhost:8000/search?query=vitamin%20D%20depression&study_types=meta_analysis&language=ru&limit=10"
```

#### Получение информации о конкретном исследовании

**GET /study/{pmid}**

```bash
curl http://localhost:8000/study/12345678
```

#### Проверка работоспособности

**GET /health**

```bash
curl http://localhost:8000/health
```

---

## 📊 Пример ответа API

```json
{
  "query": "vitamin D depression",
  "total_results": 2,
  "summary": "По запросу 'vitamin D depression' найдено 2 исследования, включая 2 высококачественных (мета-анализы, систематические обзоры или рандомизированные испытания).",
  "results": [
    {
      "pmid": "12345678",
      "title": "Effect of vitamin D supplementation on depression: a meta-analysis",
      "abstract": "This meta-analysis found that vitamin D supplementation significantly reduces depression symptoms...",
      "authors": ["Smith J", "Doe A"],
      "journal": "Journal of Clinical Medicine",
      "publication_date": "2023-05-15",
      "study_type": "meta_analysis",
      "participants": 10000,
      "confidence": "high",
      "doi": "10.1234/abc",
      "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
      "simple_explanation": "Это мета-анализ, который объединяет результаты нескольких исследований для получения более достоверных данных. Доказательства высокого качества. В нем приняли участие 10000 человек.",
      "key_findings": [
        "Витамин D значительно снижает симптомы депрессии",
        "Эффект более выражен у людей с дефицитом витамина D"
      ]
    }
  ]
}
```

---

## 🏗 Структура проекта

```
medexplainer/
├── app/
│   ├── __init__.py          # Инициализация модуля
│   ├── config.py            # Настройки приложения
│   ├── main.py              # Основное приложение FastAPI
│   ├── models.py            # Модели данных (Pydantic)
│   ├── search.py            # Поиск в PubMed
│   └── explain.py           # Упрощение текста и генерация объяснений
│
├── static/
│   └── index.html           # Веб-интерфейс
│
├── tests/
│   ├── __init__.py
│   ├── test_api.py          # Тесты API
│   ├── test_search.py       # Тесты поиска
│   └── test_explain.py      # Тесты упрощения текста
│
├── .env.example             # Пример переменных окружения
├── requirements.txt         # Зависимости
└── README.md               # Документация
```

---

## 🧪 Тестирование

Запустите тесты с помощью pytest:

```bash
pytest tests/
```

Или с подробным выводом:

```bash
pytest tests/ -v
```

---

## 📚 Поддерживаемые типы исследований

| Тип исследования | Уровень достоверности | Описание |
|------------------|----------------------|----------|
| Meta-Analysis | Высокий | Мета-анализ объединяет результаты нескольких исследований |
| Systematic Review | Высокий | Систематический обзор всей доступной информации |
| Randomized Controlled Trial (RCT) | Высокий | Рандомизированное контролируемое исследование |
| Cohort Study | Средний | Когортное исследование (наблюдение за группой) |
| Case-Control Study | Средний | Исследование "случай-контроль" |
| Cross-Sectional Study | Низкий | Поперечное исследование |
| Case Report | Очень низкий | Описание клинического случая |
| Case Series | Очень низкий | Серия клинических случаев |
| Animal Study | Очень низкий | Исследование на животных |
| In Vitro Study | Очень низкий | Лабораторное исследование |
| Review | Средний | Обзорная статья |

---

## 🔧 Технологии

- **Backend**: Python 3.10+, FastAPI
- **API клиент**: `requests`
- **Парсинг данных**: `BeautifulSoup`, `Biopython`
- **NLP**: `nltk`, `transformers` (для будущих улучшений)
- **Кэширование**: Redis
- **Тестирование**: `pytest`, `httpx`
- **Фронтенд**: HTML, CSS, JavaScript (vanilla)

---

## 📝 Примеры запросов

### Медицинские темы
- `vitamin D depression` — Влияние витамина D на депрессию
- `hypertension treatment` — Лечение гипертонии
- `diabetes type 2 prevention` — Профилактика диабета 2 типа
- `covid 19 long term effects` — Долгосрочные последствия COVID-19
- `asthma in children` — Астма у детей

### Фильтры
- **Типы исследований**: `meta_analysis`, `randomized_controlled_trial`, `systematic_review`
- **Минимальное количество участников**: `100`, `500`, `1000`
- **Год публикации**: `2023`, `2022`, `2021`
- **Язык**: `en` (английский), `ru` (русский)

---

## 🌍 Будущие улучшения

- [ ] Поддержка дополнительных источников (Cochrane, WHO, FDA)
- [ ] Интеграция с HuggingFace для более точного упрощения текста
- [ ] Система кэширования с Redis
- [ ] Аутентификация пользователей
- [ ] Сохранение истории поиска
- [ ] Экспорт результатов в PDF
- [ ] Мобильное приложение
- [ ] Расширение для браузера

---

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для своей функции (`git checkout -b feature/amazing-feature`)
3. Закоммитьте изменения (`git commit -m 'Add amazing feature'`)
4. Запушьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

---

## 📄 Лицензия

Проект распространяется под лицензией **MIT**. Подробности см. в файле `LICENSE`.

---

## 📞 Контакты

Если у вас есть вопросы или предложения, создайте **Issue** в репозитории или напишите на **mykhailo.radzik@gmail.com**.

---

**MedExplainer** — делаем медицинскую науку доступной для всех! 🩺💡
