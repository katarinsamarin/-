# SPbU exam date monitor

Мониторит расписание СПбГУ для образовательной программы «Mathematics (with additional qualification "Specialist in Research and Development")» и групп **25.Б02-мкн** и **25.Б03-мкн** в блоке **Intermediary attestation for the previous academic year 2025-2026**.

Когда в расписании появляется новая/изменённая экзаменационная запись, проект отправляет сообщение в Telegram.

## Почему GitHub Actions

Для такого проекта не нужен постоянно работающий Telegram-бот. Telegram Bot API позволяет отправить сообщение обычным HTTPS-запросом, поэтому сам монитор запускается по расписанию, проверяет сайт и завершается.

GitHub Actions подходит для этого: в публичном репозитории стандартные GitHub-hosted runners бесплатны, а scheduled workflow можно запускать с интервалом от 5 минут. См. документацию GitHub Actions.

> Важно: GitHub предупреждает, что scheduled workflow может запускаться с задержкой при высокой нагрузке. Поэтому интервал 15 минут — практичный компромисс.

## Структура

```text
exam-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── scraper.py
│   ├── telegram.py
│   ├── state.py
│   └── main.py
├── tests/
│   └── test_parser.py
├── state/
│   └── last_schedule.json
├── .gitignore
├── requirements.txt
└── README.md
```

## 1. Создай Telegram-бота

1. Открой в Telegram `@BotFather`.
2. Выполни `/newbot`.
3. Сохрани полученный token.
4. Напиши своему новому боту `/start`.

### Узнать chat_id

Локально:

```bash
export TELEGRAM_BOT_TOKEN="твой_токен"
python -m src.telegram --get-chat-id
```

После `/start` бот покажет найденные `chat_id`.

Либо можно посмотреть `getUpdates` через Telegram Bot API.

## 2. Создай GitHub repository

Для варианта с полностью бесплатным GitHub Actions репозиторий лучше сделать **public**.

Загрузи файлы этого проекта.

## 3. Добавь Secrets

В GitHub:

`Settings → Secrets and variables → Actions → New repository secret`

Добавь:

```text
TELEGRAM_BOT_TOKEN = токен от BotFather
TELEGRAM_CHAT_ID   = твой chat_id
```

Токен нельзя помещать в код или коммитить в Git.

## 4. Первый запуск

Workflow запускается автоматически каждые 15 минут.

Первый запуск **не присылает уведомление**: он только создаёт `state/last_schedule.json` с текущим состоянием расписания. Файл намеренно не входит в репозиторий до первого запуска.

Это важно, иначе после первого deploy Telegram сразу завалит тебя всеми уже существующими экзаменами.

После первого запуска в `state/last_schedule.json` появится текущий снимок.

Дальше:

```text
сайт изменился
      ↓
GitHub Actions запускает monitor
      ↓
scraper получает расписание
      ↓
сравнение с last_schedule.json
      ↓
есть новые/изменённые экзамены?
      ↓ yes
Telegram → уведомление
      ↓
новое состояние коммитится в repository
```

## 5. Что считается изменением

У записи учитываются:

- группа;
- дата;
- время;
- дисциплина;
- тип занятия/аттестации;
- преподаватель;
- аудитория;
- дополнительная текстовая информация.

Поэтому если, например, экзамен был:

```text
12.09 10:00
```

а потом стал:

```text
13.09 12:00
```

это будет обнаружено как изменение.

## 6. Ручной запуск

В GitHub:

`Actions → SPbU exam monitor → Run workflow`

В workflow есть `workflow_dispatch`, поэтому проверку можно запускать вручную.

## 7. Локальная проверка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."

python -m src.main
```

Чтобы только посмотреть, что сайт отдаёт парсеру:

```bash
python -m src.main --dry-run
```

`--dry-run` ничего в Telegram не отправляет.

## Важный нюанс сайта СПбГУ

Страница расписания может формировать часть содержимого JavaScript-ом. Поэтому scraper сначала пытается получить обычный HTML, а если нужные строки не находятся, использует Playwright/Chromium.

Это делает проект тяжелее обычного `requests + BeautifulSoup`, зато он устойчивее к динамической загрузке страницы.

## GitHub Actions

Workflow использует `ubuntu-latest`, устанавливает зависимости и запускает один короткий job. Для публичного репозитория стандартные GitHub-hosted runners бесплатны.

GitHub scheduled workflows имеют минимальный интервал 5 минут; здесь поставлено 15 минут. Также GitHub может задерживать scheduled jobs при высокой нагрузке.

## Ограничение

Сайт СПбГУ может изменить HTML-разметку. Если это произойдёт, скорее всего потребуется поправить эвристику в `src/scraper.py`. Сам Telegram и GitHub Actions при этом менять не нужно.
