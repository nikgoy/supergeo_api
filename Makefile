.PHONY: help install install-dev test test-cov test-unit test-integration clean lint format run migrate

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

install-dev:  ## Install development dependencies
	pip install -r requirements-dev.txt

test:  ## Run all tests
	pytest

test-cov:  ## Run tests with coverage report
	pytest --cov=app --cov-report=html --cov-report=term

test-unit:  ## Run unit tests only
	pytest -m "unit or not integration"

test-integration:  ## Run integration tests only
	pytest -m integration

test-watch:  ## Run tests in watch mode
	pytest-watch

clean:  ## Clean up cache and coverage files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf *.egg-info
	rm -rf dist
	rm -rf build

lint:  ## Run linting checks
	flake8 app tests
	mypy app

format:  ## Format code with black and isort
	black app tests
	isort app tests

run:  ## Run development server
	python run.py

migrate:  ## Run database migrations
	alembic upgrade head

migrate-create:  ## Create a new migration (usage: make migrate-create MSG="description")
	alembic revision --autogenerate -m "$(MSG)"

migrate-downgrade:  ## Downgrade database by one revision
	alembic downgrade -1

db-reset:  ## Reset database (drop all tables and re-migrate)
	alembic downgrade base
	alembic upgrade head

shell:  ## Open Python shell with app context
	python -i -c "from app import create_app; from app.models import *; app = create_app(); print('App loaded. Available: app, Client, Page, Visit')"

docker-build:  ## Build Docker image
	docker build -t ai-cache-layer .

docker-run:  ## Run Docker container
	docker run -p 5000:5000 --env-file .env ai-cache-layer

docker-compose-up:  ## Start all services with docker-compose
	docker-compose up -d

docker-compose-down:  ## Stop all services
	docker-compose down

docker-compose-logs:  ## Show logs from docker-compose
	docker-compose logs -f
