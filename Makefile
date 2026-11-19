.PHONY: install infra migrate seed setup stand api snapshot smoke reset lint

-include .env
export

G ?=
STAND_PORT ?= 8100
BACKEND_PORT ?= 8000

install:
	python -m pip install -r requirements.txt

infra:
	docker compose -p cloud-assistant up -d --wait

migrate:
	python -m core.db migrate

seed:
	python -m core.seed

setup: install migrate seed

stand:
	uvicorn --factory stand:build_app --host 127.0.0.1 --port $(STAND_PORT) --log-level warning

api:
	uvicorn app.main:app --host 127.0.0.1 --port $(BACKEND_PORT) --log-level warning

snapshot:
	python -m kb.build_snapshot

smoke:
	PYTHONPATH=. python tests/smoke.py $(G)

reset:
	curl -s -X POST http://127.0.0.1:$(STAND_PORT)/mock/admin/reset

lint:
	ruff check .
	ruff format --check .
