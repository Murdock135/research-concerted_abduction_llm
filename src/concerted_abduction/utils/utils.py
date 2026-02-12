from pathlib import Path

def find_project_root(current_path: str | Path) -> Path:
    current_path = Path(current_path).resolve()
    for parent in current_path.parents:
        if (parent / ".git").exists():
            return parent
    raise FileNotFoundError("Project root not found. No .git directory in parent directories.")

def load_prompt(file_path: str | Path) -> str:
    if not Path(file_path).exists():
        raise IOError("file {} not found".format(file_path))
    
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            prompt = f.read()
        except Exception as e:
            print("Error occured while reading file:\n{}".format(e))

    return prompt