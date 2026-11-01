"""Resolves the Vertex API key for evaluation runs without reading the environment."""

from pathlib import Path

from app.config import Settings

API_KEY_NAME = "GOOGLE_CLOUD_API_KEY"
REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class MissingCredentialsError(RuntimeError):
    """No usable API key was found in settings or the repo-root .env file."""


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, _separator, raw_value = stripped.partition("=")
        values[name.strip()] = raw_value.strip().strip("'\"")
    return values


def resolve_api_key(settings: Settings, env_file: Path = REPO_ROOT_ENV_FILE) -> str:
    if settings.embedding_api_key.strip():
        return settings.embedding_api_key
    from_file = parse_env_file(env_file).get(API_KEY_NAME, "")
    if not from_file.strip():
        raise MissingCredentialsError(f"{API_KEY_NAME} not found in settings or .env")
    return from_file
