"""Monolithic prototype implementing the full Concerted Abduction pipeline.

Current state:
- Loads a generated dataset from a JSON file

This file will contain a single-file implementation of:
- Hypothesis extraction (LLM-based)
- Mass function assignment (confidence-based)
- Evidence combination (Dempster's rule)

Intended as a working prototype to validate the pipeline before refactoring
into the modular ca/ package structure.

Usage:
    python scripts/pipeline_prototype.py

TODO:
    - Refactor extraction logic into ca/extractors/ (DONE)
    - Refactor mass functions into ca/mass_functions/
    - Refactor combiners into ca/combiners/
    - Add configuration-driven execution
"""
import json
from pathlib import Path

from concerted_abduction.extractors import ExtractorRegistry
from concerted_abduction.utils.run_utils import latest_run_dir, make_run_dir, save_run_metadata
from concerted_abduction.utils.utils import load_prompt
from config.settings import ENVSettings, ConcertedAbductionSettings

# -------------------------------------------------------------------
# Helpers
def load_data(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_uods(sample: dict, cfg):
    extractor_cls = ExtractorRegistry.get(cfg.type)
    extractor = extractor_cls(language_model=cfg.llm.model_name)
    extractor.set_system_prompt(load_prompt(cfg.prompt_path))

    inputs = [output["response"] for output in sample["outputs"]]
    return extractor.create_uod(inputs)

def save_hypotheses(sample_id: str, uod: dict, run_dir: Path):
    output_path = run_dir / f"{sample_id}_uod.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(uod, f, ensure_ascii=False, indent=4)
    print(f"Saved UoD for sample {sample_id} to {output_path}")
# -------------------------------------------------------------------

def main():
    """Main execution function for the pipeline prototype."""
    env = ENVSettings()
    if not env.gemini_api_key:
        raise EnvironmentError("GEMINI_API_KEY not found in environment variables.")

    settings = ConcertedAbductionSettings()
    extractor_cfg = settings.hypothesis_extractor
    if extractor_cfg.llm is None:
        raise ValueError(f"hypothesis_extractor config of type '{extractor_cfg.type}' requires an 'llm' section")

    data_path = latest_run_dir(settings.data_generator.output_dir) / "generated_dataset.json"
    dataset = load_data(data_path)
    print("Loaded dataset:\n", dataset)

    run_dir = make_run_dir(extractor_cfg.output_dir)
    save_run_metadata(
        run_dir,
        dataset_path=str(data_path),
        extractor_type=extractor_cfg.type,
        prompt_path=str(extractor_cfg.prompt_path),
        model=extractor_cfg.llm.model_name,
    )

    for sample in dataset['samples']:
        uod = extract_uods(sample, extractor_cfg)
        save_hypotheses(sample['scenario_id'], {"uod": uod}, run_dir=run_dir)

if __name__ == "__main__":
    main()
