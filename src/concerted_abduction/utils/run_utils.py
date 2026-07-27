import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def make_run_dir(base_dir: str | Path) -> Path:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = Path(base_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def latest_run_dir(base_dir: str | Path) -> Path:
    base_dir = Path(base_dir)
    run_dirs = sorted(p for p in base_dir.iterdir() if p.is_dir())
    if not run_dirs:
        raise FileNotFoundError(f"No run directories found under {base_dir}")
    return run_dirs[-1]


def save_run_metadata(run_dir: str | Path, **fields) -> None:
    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha(),
        **fields,
    }
    with open(Path(run_dir) / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
