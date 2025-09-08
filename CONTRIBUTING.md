Contributing Guide (Backend)

Structure overview
- api/: FastAPI routers (endpoints only)
- services/: Business logic and integrations
  - services/strategies/: Indicators and strategy helpers
- core/: Cross‑cutting utilities (settings, database)
- tools/: One‑off scripts for data ingestion/verification

Adding a new endpoint
1) Implement the logic in services/ (create a new module if needed)
2) Add a router under api/ that calls into the service layer
3) Register the router in backend/main.py
4) If the endpoint needs technical indicators, prefer using services/strategies

Working with strategies
- Common indicators and generic strategies live in services/strategies/strategy_common.py
- For scenario‑specific defaults:
  - Day trading: services/strategies/strategy_day.py
  - Swing/position: services/strategies/strategy_stock.py
- Keep indicator math in strategy_common, keep only defaults/wrappers in the scenario files

Note on deprecation
- backend/strategy.py is kept only as a compatibility shim and emits a DeprecationWarning.
- New code should import from services/strategies/* exclusively.

Environment and secrets
- Copy backend/.env.example to backend/.env and fill required keys
- DB settings must be provided via env (no in‑code defaults)

Dev workflow
- Run both apps: make dev
- Backend only: make dev-backend
- Frontend only: make dev-frontend
- DB helpers: make fetch-stocks | make check-industries | make verify-db
- Clean caches: make clean
