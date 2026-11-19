.PHONY: install infra migrate seed setup stand smoke reset lint

G ?=

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
	uvicorn --factory stand:build_app --host 127.0.0.1 --port $${STAND_PORT:-8100} --log-level warning

smoke:
	PYTHONPATH=. python tests/smoke.py $(G)

reset:
	curl -s -X POST http://127.0.0.1:$${STAND_PORT:-8100}/mock/admin/reset

lint:
	ruff check .
	ruff format --check .
