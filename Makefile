SHELL := /bin/bash

# Config
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 5000

.PHONY: dev dev-backend dev-frontend fetch-stocks check-industries verify-db clean-pyc clean-ds clean

dev: ## Start backend and frontend (uses dev.sh)
	./dev.sh

dev-backend: ## Run backend with uvicorn
	cd backend && python -m uvicorn main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

dev-frontend: ## Run frontend Next.js dev server
	cd frontend && npm run dev

fetch-stocks: ## Fetch TWSE stocks and upsert to DB
	cd backend && python tools/fetch_stocks.py

check-industries: ## Print industry counts from DB
	cd backend && python tools/check_industries.py

verify-db: ## Verify DB connectivity and 'stocks' table
	cd backend && python tools/verify_db.py

clean-pyc: ## Remove Python cache files
	find . -name "__pycache__" -type d -prune -exec rm -rf {} + || true
	find . -name "*.pyc" -delete || true

clean-ds: ## Remove macOS .DS_Store files
	find . -name ".DS_Store" -delete || true

clean: clean-pyc clean-ds ## Remove caches and .DS_Store
