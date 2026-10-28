# Simulation service

The deterministic strategy-mode simulation owns live world state in its own PostgreSQL database (`simulation_db`) and advances the world turn by turn. The current shipped slice includes campaign and commanded-battle backend APIs. It writes no prose and calls no memory service.

Design: [ADR-30](../../docs/adr/030-simulation-service-structure-and-persistence.md), [contracts spec](../../docs/specs/strategy-mode-contracts.spec.md), [battle spec](../../docs/specs/strategy-battles.spec.md), [validation and handoff](../../docs/reports/strategy-battle-backend-validation.md), [RFC](../../docs/strategy-mode/strategy-mode-rfc.md).

## Layout

- `app/models/` — world state, orders, API shapes, row models.
- `app/engine/` — pure turn pipeline, RNG, world hash. No I/O, no config (enforced by `lint-imports`).
- `app/repositories/` — the only files with SQL, one per table.
- `app/db/` — connection pool and the forward-only migration runner.
- Shared scenario, map and scene contracts live in [`packages/strategy-contracts/`](../../packages/strategy-contracts).

## Run

```bash
docker compose up -d simulation-postgres   # from the repo root; port 5434
cd apps/simulation
uv sync
uv run python -m app.db.migrate            # applies app/db/migrations/*.sql
uv run uvicorn app.main:app --port 8081    # GET /health
```

Authenticated browser routes cover `/v1/playthroughs/{id}/world`, campaign start, typed command acceptance, battle list/detail/reports, and one-wave advancement. Internal playthrough initialization uses `X-Internal-Service-Token`. All mutations require an operation ID and expected world/turn/wave cursor. See the contracts spec for request and response shapes.

Orders, diplomacy, sieges, internal events, time events and story checks are currently registered campaign no-op phases. Movement, battles and economy have implementations; only the economy shortfall has a code-only HTTP choice. The generic TRS scene handoff is not connected. There is no Core API or browser integration yet, and the strategy mode is not playable through the product UI.

The whole stack: `docker compose up -d simulation` (runs `simulation-migrate` first).

## Test and lint

```bash
uv run pytest -q                           # needs simulation-postgres running
uv run ruff format . && uv run ruff check . --fix
uv run lint-imports
```

Tests run against a real PostgreSQL: `simulation_test_db` is recreated and migrated on first use.
