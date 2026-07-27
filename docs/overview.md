# Overview

## The problem

When you ask several LLMs the same question — say, a medical diagnosis question — they don't agree perfectly. Each response overlaps with the others on some points and diverges on others. Naive strategies for combining these responses (majority vote, averaging, picking one model as "the truth") throw away information about *how much* the models agree and *where* they disagree.

## The idea: Concerted Abduction

This project treats each model's response as a piece of **evidence** rather than a candidate answer, and combines that evidence using **Dempster-Shafer Theory (DST)** — a mathematical framework for reasoning under uncertainty that generalizes probability theory to handle partial/incomplete belief.

The DST pipeline, conceptually:

1. **Universe of Discourse (UoD)** — the full set of possible hypotheses that any model's response could be pointing at (e.g. all candidate diagnoses mentioned across Model A/B/C's responses).
2. **Mass functions** — for each model, assign a "mass" (belief weight) to subsets of the UoD based on what that model's response supports. Unlike probability, mass can be assigned to *sets* of hypotheses, not just single ones — capturing genuine uncertainty ("it's either X or Y, but I can't tell which").
3. **Evidence combination (Dempster's rule)** — combine the mass functions from multiple models into a single belief distribution over the UoD, mathematically accounting for agreement (reinforcement) and disagreement (discounting) between sources.

The output is a reconciled belief distribution: a principled way of saying "given what all the models said, and how much they agreed or disagreed, here's the combined confidence in each hypothesis" — rather than a single point answer.

## Why medical diagnosis

Medical differential diagnosis is a natural fit: symptoms are ambiguous, multiple hypotheses are usually live at once, and clinicians already reason in a Dempster-Shafer-like way (narrowing down a set of possible conditions as evidence accumulates). It's also a domain where honestly representing uncertainty (rather than false confidence) matters.

## Status

This is early-stage research code, not a product. See [roadmap.md](roadmap.md) for what's built vs. planned. As of now:

- ✅ Synthetic dataset generation (multiple model outputs per scenario, via Gemini)
- ✅ Typed dataset schema (Pydantic)
- ✅ LLM-based hypothesis extraction (building the UoD from model outputs)
- ✅ TOML-driven configuration for components (LLM choice, prompts, examples per component)
- ❌ Mass function assignment — not implemented
- ❌ Evidence combination (Dempster's rule) — not implemented
- ❌ End-to-end pipeline — `scripts/pipeline_prototype.py` currently only runs data loading + hypothesis extraction

---
Next: [architecture.md](architecture.md) — how these pieces fit together in the codebase.
