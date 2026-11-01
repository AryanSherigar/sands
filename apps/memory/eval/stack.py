"""An isolated memory service on a scratch database; never touches the dev memory_db."""

import asyncio
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx
from psycopg import AsyncConnection, sql

from eval.errors import HarnessError

MEMORY_ROOT = Path(__file__).resolve().parents[1]
SCRATCH_PREFIX = "memory_eval_"
MAINTENANCE_DATABASE = "postgres"
CREATE_DATABASE = "CREATE DATABASE {name}"
DATABASE_EXISTS = "SELECT 1 FROM pg_database WHERE datname = %s"
DROP_DATABASE = "DROP DATABASE IF EXISTS {name} WITH (FORCE)"
HEALTH_PATH = "/health"
HEALTH_WAIT_SECONDS = 60.0
HEALTH_POLL_SECONDS = 0.5
DEFAULT_PORT = 8091
QUALITY_EMBED_TIMEOUT_SECONDS = 30.0


@dataclass
class Stack:
    database_name: str
    database_url: str
    base_url: str
    process: subprocess.Popen[bytes] | None = None


def database_url_for(base_url: str, database_name: str) -> str:
    parts = urlsplit(base_url)
    return urlunsplit(parts._replace(path=f"/{database_name}"))


async def _run_maintenance(base_url: str, template: str, name: str) -> None:
    url = database_url_for(base_url, MAINTENANCE_DATABASE)
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(sql.SQL(template).format(name=sql.Identifier(name)))


async def _database_exists(base_url: str, name: str) -> bool:
    url = database_url_for(base_url, MAINTENANCE_DATABASE)
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        cursor = await connection.execute(DATABASE_EXISTS, (name,))
        return await cursor.fetchone() is not None


def _service_env(
    database_url: str,
    api_key: str,
    embed_timeout: float,
    extraction: dict[str, str] | None = None,
) -> dict[str, str]:
    """`extraction` carries the experiment knobs (model, thinking level, prompt version)."""
    return {
        "MEMORY_DATABASE_URL": database_url,
        "EMBEDDING_API_KEY": api_key,
        "EXTRACTION_API_KEY": api_key,
        "RETRIEVAL_EMBED_TIMEOUT_SECONDS": str(embed_timeout),
        "LOG_LEVEL": "INFO",
        **(extraction or {}),
    }


def _run_migrations(env: dict[str, str]) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app.db.migrate"],
        cwd=MEMORY_ROOT,
        env=env,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise HarnessError("Migrations failed on the scratch database")


async def _is_healthy(client: httpx.AsyncClient) -> bool:
    try:
        return (await client.get(HEALTH_PATH)).status_code == httpx.codes.OK
    except httpx.TransportError:
        return False


async def _poll_health(client: httpx.AsyncClient, deadline: float) -> bool:
    while time.monotonic() < deadline:
        if await _is_healthy(client):
            return True
        await asyncio.sleep(HEALTH_POLL_SECONDS)
    return False


async def _wait_until_healthy(base_url: str) -> None:
    deadline = time.monotonic() + HEALTH_WAIT_SECONDS
    async with httpx.AsyncClient(base_url=base_url) as client:
        is_healthy = await _poll_health(client, deadline)
    if not is_healthy:
        raise HarnessError("Scratch memory service did not become healthy")


async def prepare_scratch_database(
    dev_database_url: str, run_name: str, api_key: str
) -> tuple[str, str]:
    """Creates and migrates a scratch database; returns its name and URL."""
    name = f"{SCRATCH_PREFIX}{run_name}"
    if not await _database_exists(dev_database_url, name):
        await _run_maintenance(dev_database_url, CREATE_DATABASE, name)
    url = database_url_for(dev_database_url, name)
    _run_migrations(_service_env(url, api_key, QUALITY_EMBED_TIMEOUT_SECONDS))
    return name, url


async def start_stack(
    dev_database_url: str,
    run_name: str,
    api_key: str,
    embed_timeout: float,
    log_path: Path,
    port: int = DEFAULT_PORT,
    extraction: dict[str, str] | None = None,
) -> Stack:
    name = f"{SCRATCH_PREFIX}{run_name}"
    if not await _database_exists(dev_database_url, name):
        await _run_maintenance(dev_database_url, CREATE_DATABASE, name)
    url = database_url_for(dev_database_url, name)
    env = _service_env(url, api_key, embed_timeout, extraction)
    _run_migrations(env)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)]
    process = subprocess.Popen(
        command,
        cwd=MEMORY_ROOT,
        env=env,
        stdout=log_path.open("wb"),
        stderr=subprocess.STDOUT,
    )
    stack = Stack(name, url, f"http://127.0.0.1:{port}", process)
    await _wait_until_healthy(stack.base_url)
    return stack


async def stop_stack(stack: Stack, dev_database_url: str, should_drop: bool) -> None:
    if stack.process is not None:
        stack.process.terminate()
        stack.process.wait(timeout=30)
    if should_drop:
        await _run_maintenance(dev_database_url, DROP_DATABASE, stack.database_name)
