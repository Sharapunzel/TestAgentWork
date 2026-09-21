.PHONY: test-backend test-frontend test lint dev-backend dev-frontend

test-backend:
	cd backend && uv run pytest tests/test_health.py -q

test-frontend:
	cd frontend && npm test -- --run

test: test-backend test-frontend

lint:
	cd backend && uv run ruff check app tests
	cd frontend && npm run lint

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload

dev-frontend:
	cd frontend && npm run dev
