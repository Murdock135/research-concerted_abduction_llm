# Project Structure

```
.
├── README.md                       Top-level summary (mirrors CLAUDE.md)
├── CLAUDE.md                       Instructions for Claude Code working in this repo
├── pyproject.toml                  Package metadata, deps (uv_build backend)
├── config.toml                     (optional, not present by default) project-level config overrides
│
├── src/
│   ├── concerted_abduction/        Main package
│   │   ├── types.py                 Pydantic dataset schema: ModelOutput, DataSample, DataSet
│   │   ├── data_utils/              Data generation component
│   │   │   ├── base.py               DataGenerator ABC
│   │   │   ├── registry.py           DataGeneratorRegistry
│   │   │   └── data_generator.py     CommonInputDataGenerator ("common_input")
│   │   ├── fod/                     Frame-of-discernment extraction component
│   │   │   ├── base.py               FrameOfDiscernmentExtractor ABC
│   │   │   ├── registry.py           FodExtractorRegistry
│   │   │   └── llm.py                LanguageModelFodExtractor ("language_model_fod_extractor")
│   │   ├── focal_set/               Focal-set creation component
│   │   │   ├── base.py               FocalSetCreator ABC
│   │   │   ├── registry.py           FocalSetRegistry
│   │   │   └── llm.py                LanguageModelFocalSetCreator
│   │   ├── bpa/                     Source mass assignment (base, registry, llm)
│   │   ├── combiners/               Evidence combination (base, registry, dempster)
│   │   ├── core/                    EMPTY
│   │   └── utils/
│   │       └── utils.py              find_project_root(), load_prompt()
│   └── config/
│       ├── settings.py              ENVSettings, ConcertedAbductionSettings (TOML + env loading)
│       └── default_config.toml      Bundled default component config
│
├── scripts/
│   ├── generate_data.py            Entry point: generate synthetic dataset in a timestamped run
│   ├── pipeline_prototype.py       Earlier pipeline prototype
│   └── run.py                      Entry point: extraction through evidence combination
│
├── prompts/                        System prompts for LLM-driven components
│   ├── data_generators/common_input/v0.txt
│   ├── fod/v0.txt
│   ├── focal_set/v0.txt
│   └── bpa/v0.txt
│
├── data/
│   └── synthetic/
│       ├── examples/common_input/v0.json    Few-shot examples used in the data-generation prompt
│       └── generated/common_input/<run>/    Timestamped outputs of scripts/generate_data.py
│
├── experiments/
│   └── runs/                       Timestamped pipeline stage artifacts, errors, metadata, and summary
│
├── integrations/                   Root-level (NOT under src/) — gemini.py, langchain.py, openai.py
│                                    all currently empty stub files, unused
│
├── notebooks/
│   └── scratch_gemini_api.ipynb    Scratch notebook, not part of the pipeline
│
├── tests/                          Unit tests and optional API smoke checks
│
└── docs/                           You are here
```

See [architecture.md](architecture.md) for how these pieces connect at runtime, and [configuration.md](configuration.md) for how paths like `output_dir`, `prompt_path`, `examples_path` are resolved.

---
Next: [roadmap.md](roadmap.md) — what's built vs. still to do.
