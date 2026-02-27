.PHONY: test lint run docker-up docker-down clean

test:
	python -m pytest tests/ -v --tb=short

lint:
	python -m ruff check . --fix

run:
	python bot.py

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
