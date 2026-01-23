from pathlib import Path

def find_project_root(current_path: str | Path) -> Path:
    current_path = Path(current_path).resolve()
    for parent in current_path.parents:
        if (parent / ".git").exists():
            return parent
    raise FileNotFoundError("Project root not found. No .git directory in parent directories.")