from pathlib import Path

# ---------------------------------------------------------------------------
# Filesystem paths
# ---------------------------------------------------------------------------

_DASHBOARD_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _DASHBOARD_DIR.parent
SECRETS_FILE: Path = _PROJECT_ROOT / "secrets.env"
DATA_DIR: Path = _PROJECT_ROOT / "data"
CACHE_DIR: Path = DATA_DIR / "cache"
