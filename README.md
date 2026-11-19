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
