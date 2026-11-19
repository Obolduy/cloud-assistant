# Ассистент облачного хостинга

Агентный чат в панели облачного хостинга: отвечает владельцу о сервере, конфигурации и списаниях
со ссылками на базу знаний, а смену конфигурации, услуг и контактов проводит через карточку
подтверждения. Проект к воркшопам третьего модуля профессии «LLM-разработчик» на Хекслете.

Архитектура и решения: [docs/architecture.md](docs/architecture.md), [docs/adr/](docs/adr/).

## Эталон по встречам

На каждую встречу два тега: `workshop-N-start` – код, который разбираем на встрече, и `workshop-N` –
решение домашки.

```sh
git clone https://github.com/Obolduy/cloud-assistant.git
cd cloud-assistant
git fetch --tags

# начать домашку со старта встречи
git checkout -b my-work workshop-2-start

# сравнить свое решение с эталоном
git diff workshop-2 -- app/
```

## Стек

Python 3.12, OpenAI Agents SDK, MCP (streamable HTTP), FastAPI, PostgreSQL 16 + pgvector,
Dogwood (политики), JWT RS256. Модель – любая с OpenAI-совместимым API, по умолчанию локальная в
LM Studio.

## Что есть сейчас (`workshop-1`)

- Postgres 16 с pgvector в Docker Compose, схема и миграции SQL-файлами.
- Сид из `data/demo.yaml`: конфигурации, услуги, аккаунт Анны с сервером на «Стандарте» и бэкапами,
  пользователи `anna`, `boris`, `olga`, списания.
- REST-моки стенда: аккаунт, каталог конфигураций и услуг, списания, тикеты.
- Биллинг: смена конфигурации с ключом идемпотентности (повтор возвращает прежний результат),
  дневной лимит, правила `same_plan`, `disk_downgrade`, `unknown_plan`.
- Деньги – целые копейки, форматирование одной функцией `format_rub`.

## Запуск

Нужны Python 3.12 и Docker.

```sh
python3.12 -m venv .venv && source .venv/bin/activate
make install
cp .env.example .env   # порт 5436 занят? поменяйте PG_PORT и PG_DSN
make infra && make migrate && make seed
make stand             # http://127.0.0.1:8100/health
```

```sh
make smoke G=0   # проверки стенда без модели, стенд должен быть запущен
make lint
make reset       # вернуть демо-данные
```

## Как проверить себя

- `make smoke G=0` и `make lint` зеленые.
- Списания Анны за `2026-11` – 124 000 копеек (1 240 ₽).
- Смена конфигурации с тем же ключом дважды – одна операция и тот же ответ.
- Четвертая смена за сутки – `daily_limit`, Стандарт → Старт – `disk_downgrade`.
- `make reset` возвращает все к сиду.
