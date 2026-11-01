"""THROWAWAY queue spike (Task 5): can procrastinate replace our SKIP LOCKED claim code?

NOT part of the service and never imported by it. Needs a scratch venv with
`procrastinate>=3,<4`, `psycopg[binary]`, `psycopg_pool`, `pydantic-settings`,
`structlog`, `pgvector` installed; do NOT add procrastinate to requirements.txt.
`app` is imported only to drive the real migration runner, so the runner must be
importable (run from apps/memory/). Not covered by the import-linter contracts
(root_package = "app"; this file lives outside it).

    cd apps/memory
    <scratch-venv>/bin/python -m scripts.spike_queue            # creates + drops memory_spike_db
    <scratch-venv>/bin/python -m scripts.spike_queue --keep-db  # leave the scratch DB behind

Talks only to the scratch database `memory_spike_db` on the compose Postgres.
"""

import argparse
import asyncio
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import procrastinate
from app.db import migrate
from procrastinate import exceptions as procrastinate_exceptions
from procrastinate import jobs as procrastinate_jobs
from procrastinate import retry as procrastinate_retry
from procrastinate.schema import SchemaManager
from psycopg import AsyncConnection, sql
from psycopg.conninfo import make_conninfo
from psycopg_pool import AsyncConnectionPool

MAINTENANCE_DSN = os.environ.get(
    "SPIKE_MAINTENANCE_URL", "postgresql://memory_db:memory_db@127.0.0.1:5433/postgres"
)
SPIKE_DB_NAME = "memory_spike_db"
SPIKE_DSN = make_conninfo(MAINTENANCE_DSN, dbname=SPIKE_DB_NAME)
SERVICE_MIGRATIONS = Path(__file__).parent.parent / "app" / "db" / "migrations"
VENDORED_MIGRATION_NAME = "0005_procrastinate_schema.sql"
POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 10  # mirrors app/config.py defaults

CREATE_RUNS = (
    "CREATE TABLE IF NOT EXISTS spike_runs ("
    "label text, lock_key text, actor text, "
    "started timestamptz, ended timestamptz)"
)
RETRY_DELAYS_SECONDS = (1.0, 5.0, 15.0)  # 1, 5, 15 minutes, 1 minute -> 1 second
TIMING_TOLERANCE_SECONDS = 0.6

app = procrastinate.App(connector=procrastinate.PsycopgConnector())


async def record_run(label: str, lock_key: str | None, seconds: float) -> None:
    actor = f"pid{os.getpid()}"
    async with await AsyncConnection.connect(SPIKE_DSN, autocommit=True) as connection:
        cursor = await connection.execute("SELECT clock_timestamp()")
        started = (await cursor.fetchone())[0]
        await asyncio.sleep(seconds)
        cursor = await connection.execute("SELECT clock_timestamp()")
        ended = (await cursor.fetchone())[0]
        await connection.execute(
            "INSERT INTO spike_runs VALUES (%s, %s, %s, %s, %s)",
            (label, lock_key, actor, started, ended),
        )


@app.task(name="sleepy")
async def sleepy(label: str, seconds: float, lock_key: str | None = None) -> None:
    await record_run(label, lock_key, seconds)


class ScheduleRetryStrategy(procrastinate_retry.BaseRetryStrategy):
    """Retry i waits delays[i]; no retry once len(delays) retries were used."""

    def __init__(self, delays: tuple[float, ...]) -> None:
        self.delays = delays

    def get_retry_decision(
        self, *, exception: BaseException, job: procrastinate_jobs.Job
    ) -> procrastinate_retry.RetryDecision | None:
        if job.attempts >= len(self.delays):
            return None
        return procrastinate_retry.RetryDecision(
            retry_in={"seconds": self.delays[job.attempts]}
        )


@app.task(name="flaky", retry=ScheduleRetryStrategy(RETRY_DELAYS_SECONDS))
async def flaky(label: str) -> None:
    await record_run(label, None, 0)
    raise RuntimeError("retryable failure")


# ---------------------------------------------------------------- infrastructure


async def _maintenance(statement: str) -> None:
    async with await AsyncConnection.connect(
        MAINTENANCE_DSN, autocommit=True
    ) as connection:
        await connection.execute(
            sql.SQL(statement).format(sql.Identifier(SPIKE_DB_NAME))
        )


async def create_scratch_database() -> None:
    await _maintenance("DROP DATABASE IF EXISTS {} WITH (FORCE)")
    await _maintenance("CREATE DATABASE {}")


async def drop_scratch_database() -> None:
    await _maintenance("DROP DATABASE IF EXISTS {} WITH (FORCE)")


def stage_migrations(directory: Path) -> str:
    """Copy the service's real migrations and vendor procrastinate's schema next to them."""
    for path in SERVICE_MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        shutil.copy(path, directory / path.name)
    schema_sql = SchemaManager.get_schema()
    (directory / VENDORED_MIGRATION_NAME).write_text(schema_sql, encoding="utf-8")
    return schema_sql


async def apply_via_service_runner() -> dict[str, object]:
    """Run the service's actual runner (one txn per file, checksum, advisory lock)."""
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        schema_sql = stage_migrations(directory)
        original = migrate.MIGRATIONS_DIRECTORY
        migrate.MIGRATIONS_DIRECTORY = directory
        try:
            first = await migrate.apply_migrations(SPIKE_DSN)
            second = await migrate.apply_migrations(SPIKE_DSN)
        finally:
            migrate.MIGRATIONS_DIRECTORY = original
    return {"first": first, "second": second, "schema_bytes": len(schema_sql)}


async def scalar(query: str, params: tuple = ()) -> object:
    async with await AsyncConnection.connect(SPIKE_DSN, autocommit=True) as connection:
        cursor = await connection.execute(query, params)
        return (await cursor.fetchone())[0]


async def rows(query: str, params: tuple = ()) -> list[tuple]:
    async with await AsyncConnection.connect(SPIKE_DSN, autocommit=True) as connection:
        cursor = await connection.execute(query, params)
        return await cursor.fetchall()


async def reset_state() -> None:
    async with await AsyncConnection.connect(SPIKE_DSN, autocommit=True) as connection:
        await connection.execute(CREATE_RUNS)
        await connection.execute(
            "TRUNCATE spike_runs, procrastinate_jobs, procrastinate_events, "
            "procrastinate_workers RESTART IDENTITY CASCADE"
        )


async def job_statuses() -> dict[str, int]:
    found = await rows(
        "SELECT status::text, count(*) FROM procrastinate_jobs GROUP BY 1"
    )
    return {status: count for status, count in found}


async def backend_count() -> int:
    return await scalar(
        "SELECT count(*) FROM pg_stat_activity WHERE datname = %s "
        "AND pid <> pg_backend_pid()",
        (SPIKE_DB_NAME,),
    )


def open_service_shaped_pool() -> AsyncConnectionPool:
    return AsyncConnectionPool(
        conninfo=SPIKE_DSN, min_size=POOL_MIN_SIZE, max_size=POOL_MAX_SIZE, open=False
    )


WORKER_KWARGS = {"install_signal_handlers": False, "fetch_job_polling_interval": 0.1}


def runtime_footprint() -> tuple[int, int]:
    others = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    return threading.active_count(), len(others)


# ---------------------------------------------------------------- criterion 1


async def defer_sleepy(count: int, seconds: float, prefix: str = "j") -> None:
    for index in range(count):
        await sleepy.defer_async(label=f"{prefix}{index}", seconds=seconds)


async def test_drain_and_exit(pool: AsyncConnectionPool) -> dict[str, object]:
    result: dict[str, object] = {}
    baseline = runtime_footprint()
    await reset_state()
    started = time.monotonic()
    await app.run_worker_async(wait=False, **WORKER_KWARGS)
    result["empty_queue_return_seconds"] = round(time.monotonic() - started, 3)

    await defer_sleepy(8, 0.15)
    started = time.monotonic()
    async with asyncio.timeout(30):
        await app.run_worker_async(wait=False, concurrency=2, **WORKER_KWARGS)
    result["drain_seconds"] = round(time.monotonic() - started, 3)
    result["statuses_after_drain"] = await job_statuses()
    result["footprint_delta"] = tuple(
        now - before for now, before in zip(runtime_footprint(), baseline, strict=True)
    )
    stats = pool.get_stats()
    result["pool_in_use_after"] = stats["pool_size"] - stats["pool_available"]
    result["listener_backends_left"] = await listener_backends_left(pool)

    result.update(await deadline_graceful_case())
    result.update(await deadline_hard_cap_case())
    result.update(await listener_connection_case(pool))
    return result


async def listener_backends_left(pool: AsyncConnectionPool) -> int:
    del pool
    await asyncio.sleep(0.3)
    return await scalar(
        "SELECT count(*) FROM pg_stat_activity WHERE datname = %s "
        "AND query ILIKE 'LISTEN%%'",
        (SPIKE_DB_NAME,),
    )


async def deadline_graceful_case() -> dict[str, object]:
    await reset_state()
    await sleepy.defer_async(label="slow", seconds=1.5)
    await defer_sleepy(5, 0.1, prefix="queued")
    baseline = runtime_footprint()
    started = time.monotonic()
    timed_out = False
    try:
        async with asyncio.timeout(0.4):
            await app.run_worker_async(wait=False, concurrency=1, **WORKER_KWARGS)
    except TimeoutError:
        timed_out = True
    elapsed = round(time.monotonic() - started, 3)
    slow_status = await scalar(
        "SELECT status::text FROM procrastinate_jobs WHERE args->>'label' = 'slow'"
    )
    return {
        "deadline_timed_out": timed_out,
        "deadline_return_seconds": elapsed,
        "deadline_inflight_status": slow_status,
        "deadline_statuses": await job_statuses(),
        "deadline_footprint_delta": tuple(
            now - before
            for now, before in zip(runtime_footprint(), baseline, strict=True)
        ),
    }


async def deadline_hard_cap_case() -> dict[str, object]:
    await reset_state()
    await sleepy.defer_async(label="stuck", seconds=5.0)
    started = time.monotonic()
    try:
        async with asyncio.timeout(0.3):
            await app.run_worker_async(
                wait=False,
                concurrency=1,
                shutdown_graceful_timeout=0.5,
                **WORKER_KWARGS,
            )
    except TimeoutError:
        pass
    return {
        "hardcap_return_seconds": round(time.monotonic() - started, 3),
        "hardcap_statuses": await job_statuses(),
        "hardcap_worker_rows": await scalar(
            "SELECT count(*) FROM procrastinate_workers"
        ),
    }


async def listener_connection_case(pool: AsyncConnectionPool) -> dict[str, object]:
    result: dict[str, object] = {}
    for is_listening in (True, False):
        await reset_state()
        await sleepy.defer_async(label="hold", seconds=1.0)
        idle = await backend_count()
        peak: dict[str, int] = {}

        async def sample(peak: dict[str, int] = peak) -> None:
            await asyncio.sleep(0.5)
            peak["backends"] = await backend_count()
            peak["listen_sessions"] = await listener_backends_left(pool)

        sampler = asyncio.create_task(sample())
        await app.run_worker_async(
            wait=False, listen_notify=is_listening, **WORKER_KWARGS
        )
        await sampler
        result[f"listen_notify={is_listening}"] = {
            "backends_idle": idle,
            "backends_while_running": peak["backends"],
            "listen_sessions_while_running": peak["listen_sessions"],
            "pool_size": pool.get_stats()["pool_size"],
        }
    return result


# ---------------------------------------------------------------- criterion 2


def load_intervals(
    found: list[tuple],
) -> dict[str, list[tuple[datetime, datetime, str]]]:
    by_key: dict[str, list[tuple[datetime, datetime, str]]] = {}
    for label, key, _actor, started, ended in found:
        by_key.setdefault(key, []).append((started, ended, label))
    return {key: sorted(value) for key, value in by_key.items()}


def count_overlaps(
    intervals: dict[str, list[tuple[datetime, datetime, str]]],
) -> tuple[int, int]:
    same_key = cross_key = 0
    flat = [(key, s, e) for key, value in intervals.items() for s, e, _ in value]
    for i, (key_a, start_a, end_a) in enumerate(flat):
        for key_b, start_b, end_b in flat[i + 1 :]:
            if start_a < end_b and start_b < end_a:
                if key_a == key_b:
                    same_key += 1
                else:
                    cross_key += 1
    return same_key, cross_key


async def defer_locked_jobs(keys: list[str], per_key: int, seconds: float) -> None:
    for index in range(per_key):
        for key in keys:
            await sleepy.configure(lock=key).defer_async(
                label=f"{key}-{index}", seconds=seconds, lock_key=key
            )


async def summarize_lock_run(per_key: int, keys: list[str]) -> dict[str, object]:
    found = await rows("SELECT label, lock_key, actor, started, ended FROM spike_runs")
    intervals = load_intervals(found)
    same_key, cross_key = count_overlaps(intervals)
    in_order = all(
        [label for _, _, label in value] == [f"{key}-{i}" for i in range(per_key)]
        for key, value in intervals.items()
    )
    return {
        "jobs_run": len(found),
        "same_key_overlaps": same_key,
        "cross_key_overlaps": cross_key,
        "fifo_within_key": in_order,
        "actors": sorted({row[2] for row in found}),
        "statuses": await job_statuses(),
    }


async def test_lock_in_process(pool: AsyncConnectionPool) -> dict[str, object]:
    del pool
    keys = ["pt-A", "pt-B", "pt-C", "pt-D"]
    result: dict[str, object] = {}
    for name, workers, concurrency in (
        ("3 workers x concurrency 1, wait=False", 3, 1),
        ("1 worker x concurrency 4, wait=False", 1, 4),
    ):
        await reset_state()
        await defer_locked_jobs(keys, per_key=3, seconds=0.4)
        async with asyncio.timeout(60):
            await asyncio.gather(
                *(
                    app.run_worker_async(
                        wait=False,
                        concurrency=concurrency,
                        name=f"w{i}",
                        **WORKER_KWARGS,
                    )
                    for i in range(workers)
                )
            )
        result[name] = await summarize_lock_run(3, keys)
    result["stranded_case"] = await lock_blocked_drain_case()
    return result


async def lock_blocked_drain_case() -> dict[str, object]:
    """2 keys x 3 jobs, 1 worker with 4 slots and wait=False: blocked jobs are invisible to fetch."""
    await reset_state()
    await defer_locked_jobs(["pt-A", "pt-B"], per_key=3, seconds=0.4)
    async with asyncio.timeout(60):
        await app.run_worker_async(wait=False, concurrency=4, **WORKER_KWARGS)
    left_after_one_drain = await job_statuses()
    async with asyncio.timeout(60):
        await asyncio.gather(
            *(
                app.run_worker_async(
                    wait=False, concurrency=1, name=f"s{i}", **WORKER_KWARGS
                )
                for i in range(2)
            )
        )
    return {
        "statuses_after_single_wait_false_drain_concurrency_4": left_after_one_drain,
        "statuses_after_2_workers_concurrency_1": await job_statuses(),
    }


def spawn_worker_process(name: str) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "scripts.spike_queue",
            "--role",
            "worker",
            "--name",
            name,
        ],
        cwd=Path(__file__).resolve().parent.parent,
        stdout=subprocess.DEVNULL,
    )


async def test_lock_cross_process() -> dict[str, object]:
    keys = ["pt-A", "pt-B", "pt-C", "pt-D"]
    await reset_state()
    await defer_locked_jobs(keys, per_key=3, seconds=0.5)
    workers = [spawn_worker_process("proc1"), spawn_worker_process("proc2")]
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        statuses = await job_statuses()
        if statuses.get("succeeded", 0) == len(keys) * 3:
            break
        await asyncio.sleep(0.2)
    for process in workers:
        process.send_signal(signal.SIGTERM)
    exit_codes = [process.wait(timeout=20) for process in workers]
    summary = await summarize_lock_run(3, keys)
    summary["worker_exit_codes"] = exit_codes
    return summary


# ---------------------------------------------------------------- criterion 3


async def event_times(job_id: int) -> list[tuple[str, datetime]]:
    return await rows(
        "SELECT type::text, at FROM procrastinate_events WHERE job_id = %s ORDER BY id",
        (job_id,),
    )


async def test_retry_backoff() -> dict[str, object]:
    """Deployment model: no worker lives during backoff; a fresh drain runs every sweep."""
    await reset_state()
    job_id = await flaky.defer_async(label="always-fails")
    deadline = time.monotonic() + 90
    final_status = "todo"
    sweeps = 0
    while time.monotonic() < deadline and final_status != "failed":
        async with asyncio.timeout(30):
            await app.run_worker_async(wait=False, **WORKER_KWARGS)
        sweeps += 1
        final_status = await scalar(
            "SELECT status::text FROM procrastinate_jobs WHERE id = %s", (job_id,)
        )
        await asyncio.sleep(0.25)

    starts = [
        row[0] for row in await rows("SELECT started FROM spike_runs ORDER BY started")
    ]
    gaps = [round((b - a).total_seconds(), 2) for a, b in pairwise(starts)]
    attempts = await scalar(
        "SELECT attempts FROM procrastinate_jobs WHERE id = %s", (job_id,)
    )
    events = [name for name, _ in await event_times(job_id)]
    return {
        "final_status": final_status,
        "attempts_column": attempts,
        "executions": len(starts),
        "sweeps": sweeps,
        "gaps_between_executions_seconds": gaps,
        "configured_delays_seconds": list(RETRY_DELAYS_SECONDS),
        "events": events,
        "gaps_match": len(gaps) == len(RETRY_DELAYS_SECONDS)
        and all(
            0 <= gap - delay <= TIMING_TOLERANCE_SECONDS
            for gap, delay in zip(gaps, RETRY_DELAYS_SECONDS, strict=True)
        ),
    }


async def test_retry_holds_lock_order() -> dict[str, object]:
    """A backing-off job for a lock key must keep later jobs for that key waiting."""
    await reset_state()
    await flaky.configure(lock="pt-R").defer_async(label="R-first")
    await sleepy.configure(lock="pt-R").defer_async(
        label="R-second", seconds=0.1, lock_key="pt-R"
    )
    worker = asyncio.create_task(
        app.run_worker_async(wait=True, concurrency=2, **WORKER_KWARGS)
    )
    await asyncio.sleep(3.0)
    second_ran_during_backoff = bool(
        await scalar("SELECT count(*) FROM spike_runs WHERE label = 'R-second'")
    )
    worker.cancel()
    await asyncio.gather(worker, return_exceptions=True)
    return {"later_same_key_job_ran_during_backoff": second_ran_during_backoff}


# ---------------------------------------------------------------- crash recovery


async def test_crash_recovery(pool: AsyncConnectionPool) -> dict[str, object]:
    del pool
    await reset_state()
    await sleepy.configure(lock="pt-X").defer_async(
        label="X-crashes", seconds=30, lock_key="pt-X"
    )
    await sleepy.configure(lock="pt-X").defer_async(
        label="X-after", seconds=0.1, lock_key="pt-X"
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "scripts.spike_queue", "--role", "crash-worker"],
        cwd=Path(__file__).resolve().parent.parent,
        stdout=subprocess.DEVNULL,
    )
    for _ in range(100):
        if (await job_statuses()).get("doing"):
            break
        await asyncio.sleep(0.1)
    process.kill()
    process.wait()

    async with asyncio.timeout(30):
        await app.run_worker_async(wait=False, **WORKER_KWARGS)
    statuses_after_crash_and_drain = await job_statuses()
    await asyncio.sleep(2.0)
    stalled = await app.job_manager.get_stalled_jobs(seconds_since_heartbeat=1.0)
    for job in stalled:
        await app.job_manager.retry_job_by_id_async(
            job_id=job.id, retry_at=datetime.now(UTC)
        )
    async with asyncio.timeout(60):
        await app.run_worker_async(
            wait=False, **{**WORKER_KWARGS, "stalled_worker_timeout": 1.0}
        )
    return {
        "drain_after_kill_statuses": statuses_after_crash_and_drain,
        "stalled_jobs_found_by_get_stalled_jobs": len(stalled),
        "statuses_after_manual_stalled_retry": await job_statuses(),
    }


# ---------------------------------------------------------------- verdicts


def check_drain(outcome: dict[str, object]) -> list[tuple[str, bool]]:
    return [
        (
            "drain returns; all 8 jobs succeeded",
            outcome["statuses_after_drain"] == {"succeeded": 8},
        ),
        ("no extra thread/task left behind", outcome["footprint_delta"] == (0, 0)),
        ("no pool connection held after return", outcome["pool_in_use_after"] == 0),
        ("no LISTEN session left after return", outcome["listener_backends_left"] == 0),
        (
            "empty queue returns immediately (<1s)",
            outcome["empty_queue_return_seconds"] < 1.0,
        ),
        (
            "deadline: in-flight job finished, rest stay todo",
            outcome["deadline_inflight_status"] == "succeeded"
            and outcome["deadline_statuses"] == {"succeeded": 1, "todo": 5},
        ),
        (
            "deadline: nothing left running",
            outcome["deadline_footprint_delta"] == (0, 0),
        ),
        (
            "hard cap: overrunning job marked aborted, worker row removed, not left 'doing'",
            outcome["hardcap_statuses"] == {"aborted": 1}
            and outcome["hardcap_worker_rows"] == 0,
        ),
    ]


def check_lock_run(summary: dict[str, object]) -> bool:
    return (
        summary["jobs_run"] == 12
        and summary["same_key_overlaps"] == 0
        and summary["cross_key_overlaps"] > 0
        and summary["fifo_within_key"] is True
    )


def check_lock_in_process(outcome: dict[str, object]) -> list[tuple[str, bool]]:
    return [
        (name, check_lock_run(value))
        for name, value in outcome.items()
        if name != "stranded_case"
    ]


def check_lock_cross_process(outcome: dict[str, object]) -> list[tuple[str, bool]]:
    return [
        (
            "two OS processes, no same-key overlap, cross-key overlap, FIFO",
            check_lock_run(outcome),
        ),
        ("both processes ran jobs", len(outcome["actors"]) == 2),
    ]


def check_retry(outcome: dict[str, object]) -> list[tuple[str, bool]]:
    return [
        ("ends failed", outcome["final_status"] == "failed"),
        ("ran 1 + 3 retries", outcome["executions"] == len(RETRY_DELAYS_SECONDS) + 1),
        (
            "attempt count observable",
            outcome["attempts_column"] == len(RETRY_DELAYS_SECONDS) + 1,
        ),
        ("gaps follow the 1/5/15 schedule", outcome["gaps_match"] is True),
    ]


def check_lock_order(outcome: dict[str, object]) -> list[tuple[str, bool]]:
    return [
        (
            "later same-key job waits out a retrying job",
            not outcome["later_same_key_job_ran_during_backoff"],
        )
    ]


def check_nothing(outcome: dict[str, object]) -> list[tuple[str, bool]]:
    del outcome
    return []


# ---------------------------------------------------------------- roles + main


async def run_worker_role(name: str) -> None:
    pool = open_service_shaped_pool()
    async with pool, app.open_async(pool):
        await app.run_worker_async(
            wait=True, concurrency=2, name=name, fetch_job_polling_interval=0.1
        )


async def run_crash_worker_role() -> None:
    pool = open_service_shaped_pool()
    async with pool, app.open_async(pool):
        await app.run_worker_async(
            wait=True,
            concurrency=1,
            install_signal_handlers=False,
            update_heartbeat_interval=0.3,
            fetch_job_polling_interval=0.1,
        )


async def run_all(keep_database: bool) -> int:
    await create_scratch_database()
    failures = 0
    try:
        print("migration runner:", await apply_via_service_runner())
        pool = open_service_shaped_pool()
        async with pool, app.open_async(pool):
            await reset_state()
            for label, coroutine, evaluate in (
                ("1 drain-and-exit", test_drain_and_exit(pool), check_drain),
                (
                    "2a lock, in-process workers",
                    test_lock_in_process(pool),
                    check_lock_in_process,
                ),
                (
                    "2b lock, cross-process workers",
                    test_lock_cross_process(),
                    check_lock_cross_process,
                ),
                (
                    "3 retry with backoff (drain sweeps)",
                    test_retry_backoff(),
                    check_retry,
                ),
                (
                    "3b retry keeps lock order",
                    test_retry_holds_lock_order(),
                    check_lock_order,
                ),
                (
                    "4 crash recovery (informational)",
                    test_crash_recovery(pool),
                    check_nothing,
                ),
            ):
                failures += await report(label, coroutine, evaluate)
    finally:
        if not keep_database:
            await drop_scratch_database()
    return failures


async def report(label: str, coroutine, evaluate) -> int:
    print(f"\n=== {label} ===")
    try:
        outcome = await coroutine
    except (TimeoutError, procrastinate_exceptions.ProcrastinateException) as error:
        print("ERROR:", repr(error))
        return 1
    for key, value in outcome.items():
        print(f"  {key}: {value}")
    failed = 0
    for name, is_ok in evaluate(outcome):
        print(f"  [{'PASS' if is_ok else 'FAIL'}] {name}")
        failed += 0 if is_ok else 1
    return failed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", default="main")
    parser.add_argument("--name", default="worker")
    parser.add_argument("--keep-db", action="store_true")
    args = parser.parse_args()
    if args.role == "worker":
        asyncio.run(run_worker_role(args.name))
        return
    if args.role == "crash-worker":
        asyncio.run(run_crash_worker_role())
        return
    sys.exit(1 if asyncio.run(run_all(args.keep_db)) else 0)


if __name__ == "__main__":
    main()
