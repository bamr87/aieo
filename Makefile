.PHONY: help install verify dev up down logs test lint format clean

help:
	@echo "Available commands:"
	@echo "  make install   - Run installation script"
	@echo "  make verify    - Verify installation"
	@echo "  make dev       - Start development environment"
	@echo "  make up        - Start Docker services"
	@echo "  make down      - Stop Docker services"
	@echo "  make logs      - View Docker logs"
	@echo "  make test      - Run tests"
	@echo "  make lint      - Run linters"
	@echo "  make format    - Format code"
	@echo "  make clean     - Clean up generated files"

install:
	@./scripts/install.sh

verify:
	@./scripts/verify.sh

dev: up
	@echo "Starting development environment..."
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "Services are ready!"

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	cd backend && pytest

lint:
	cd backend && ruff check .
	cd backend && mypy app

format:
	cd backend && black .
	cd backend && ruff check --fix .

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +

