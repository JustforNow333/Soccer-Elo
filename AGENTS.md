# Repository Guidelines

## Project Structure & Module Organization
- **Backend root** hosts operational scripts (`api_import.py`, `scheduler_manager.py`, `daily_elo_maintenance.py`) plus the Flask entry points `app.py`, `start_system.py`, and `background_worker.py`. Treat these files as the source of truth for automation and data ingest pipelines.
- **`utils/`** contains shared helpers used by importers and workers; update helpers here before duplicating logic.
- **`Frontend/`** is a Next.js 15 App Router project (TypeScript, Tailwind, shadcn/ui). All UI work stays inside this directory.
- **`legacy/`** and `temp_repo/` store historical experiments; touch them only when migrating old logic.
- Tests and fixtures currently live alongside their targets (e.g., `test_fix.py`). Keep new tests close to the code they exercise.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` — install backend dependencies.
- `python start_system.py` — interactive local orchestration (runs imports, jobs, health checks).
- `python app.py` — start the Flask API for manual verification.
- `python scheduler_manager.py --status|--daemon` — inspect or run the APScheduler daemon.
- `cd Frontend && npm install` — install UI dependencies.
- `cd Frontend && npm run dev` — Next.js dev server at `localhost:3000`.
- `cd Frontend && npm run build` — production build prior to deployment.

## Coding Style & Naming Conventions
- Python code follows PEP 8: 4-space indentation, descriptive snake_case for variables/functions, PascalCase for classes, and mandatory type hints plus docstrings on new modules.
- Prefer pure functions in `utils/` and keep side-effects inside orchestrators (`run_complete_import.py`, `initialize_and_run.py`).
- Frontend components live in PascalCase files under `Frontend/app` or `Frontend/components`; hooks stay in `Frontend/hooks` with camelCase names.
- Run `black` (line length 100) and `ruff` if you touch backend Python; run `npm run lint` before committing frontend changes.

## Testing Guidelines
- Use `pytest` for backend modules and name files `test_<module>.py`. Target ≥80% coverage on any new subsystem; mock external APIs (`API_FOOTBALL_KEY`) to avoid live calls.
- Frontend tests belong in `Frontend/__tests__/` or colocated `*.test.tsx` files executed via `npm test` (Vitest/Jest compatible). Snapshot updates require reviewer approval.

## Commit & Pull Request Guidelines
- Write conventional commits (`feat:`, `fix:`, `chore:`) in the imperative mood, e.g., `feat: add daily fixtures refresher`.
- Each PR should include: purpose summary, linked issue or ticket, testing evidence (`pytest`, `npm run dev`, etc.), and screenshots for UI-affecting work.
- Keep changes atomic; backend data migrations must ship with rollback notes and updated scripts.

## Security & Configuration Tips
- Store secrets in `.env` or deployment environment variables only; never commit `.env` or persistent credentials.
- When running schedulers or background workers, confirm `DATABASE_URL`, `API_FOOTBALL_KEY`, and Stripe keys are set to non-production values.
- Sanitize logs before sharing (PII or API responses) and prefer parameterized SQL via SQLAlchemy models (`db.py`).
