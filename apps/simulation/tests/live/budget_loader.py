import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
LEDGER_PATH = REPO_ROOT / "docs" / "reports" / "live-muse-token-ledger.md"
_MODULE_PATH = REPO_ROOT / "scripts" / "live_budget.py"


def _load():
    spec = importlib.util.spec_from_file_location("live_budget", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


live_budget = _load()
