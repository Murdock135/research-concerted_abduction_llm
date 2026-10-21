# How it works


```mermaid
flowchart LR
    Q["Hi LM, I have headache, I'm tired and thirsty. I've done x y z tests ..."]

    A["LM 1<br/>“Flu seems likely, though<br/>COVID is still possible.”"]
    B["LM 2<br/>“COVID seems more likely,<br/>but flu cannot be ruled out.”"]

    Q --> A
    Q --> B

    subgraph INTERPRET[" "]
        H["Frame of discernment<br/>{Flu, COVID}"]
        F["Extract focal sets<br/>A supports: {Flu}, {Flu, COVID}<br/>B supports: {COVID}, {Flu, COVID}"]
        MA["Assign belief masses · A<br/>80% → Flu<br/>20% → Flu OR COVID"]
        MB["Assign belief masses · B<br/>50% → COVID<br/>50% → Flu OR COVID"]

        H --> F
        F --> MA
        F --> MB
    end

    A --> H
    B --> H

    subgraph FUSE["DST · Combine the evidence"]
        C["Apply Dempster’s rule"]
        R["Combined masses<br/>66.7% → Flu<br/>16.7% → COVID<br/>16.7% → Flu OR COVID"]
        K["Conflict: 40%"]
        
        C --> R
        C --> K
    end

    MA --> C
    MB --> C

    classDef source fill:#F1F5F9,stroke:#64748B,color:#0F172A
    classDef llm fill:#DBEAFE,stroke:#3B82F6,color:#1E3A8A
    classDef dst fill:#D1FAE5,stroke:#10B981,color:#064E3B
    classDef conflict fill:#FEE2E2,stroke:#DC2626,color:#B91C1C

    class Q,A,B source
    class H,F,MA,MB llm
    class C,R dst
    class K conflict
```

[Standalone diagram source](diagrams/pipeline-overview.mmd)

## Synthetic data generator

The data generator is an LM that generates simulated converstions between a human and multiple 'experts'. The human tells the expert their problem, the experts provide their opinions independently (they don't discuss with each other).

For example, a synthetic conversation could look like this:

> **Human:** “I've had a fever, headache, body aches, and a dry cough since yesterday. What could be causing this?”
>
> **Model A:** “Flu seems most likely given the sudden fever and body aches, though COVID is also possible.”
>
> **Model B:** “COVID seems most likely, but flu could explain these symptoms too.”
>
> **Model C:** “Both flu and COVID are plausible. The symptoms alone don't clearly distinguish between them.”

> [!NOTE]
> Models 'A', 'B' and 'C' are *pretend models* and not real.

Generation is run with:

```bash
uv run python scripts/generate_data.py
```

See:

[generation script](../scripts/generate_data.py),
[system prompt](../prompts/data_generators/common_input/v0.txt), and
[examples for the data-generator LM](../data/synthetic/examples/common_input/v0.json)

## Detailed pipeline picture

```mermaid
flowchart TB
    subgraph DATA_IO["Experiment preparation · Generate synthetic data"]
        direction LR
        GI["Generation instructions<br/>Create a symptom question<br/>and contrasting responses"]
        GP["LM"]
        GO["Question + responses<br/>A: Flu likely; COVID possible<br/>B: COVID likely; flu possible"]
        GI --> GP --> GO
    end

    subgraph PIPELINE["Concerted Abduction pipeline"]
        direction TB
        subgraph FRAME_IO["1 · Extract frame of discernment"]
            direction LR
            HI["All expert opinions:<br/>A's text + B's text"]
            HP["LM"]
            HO["Frame of discernment<br/>{Flu, COVID}"]
            HI --> HP --> HO
        end

        subgraph FOCAL_IO["2 · Extract focal sets"]
            direction LR
            FI["Frame of discernment<br/>+ all source responses"]
            FP["LM"]
            FO["Focal sets for each source<br/>A: {Flu}, {Flu, COVID}<br/>B: {COVID}, {Flu, COVID}<br/>Each with justification + source excerpts"]
            FI --> FP --> FO
        end

        subgraph MASS_IO["3 · Assign belief masses"]
            direction LR
            MI["For each source separately:<br/>Its response + its focal sets<br/>+ the shared frame"]
            MP["LM"]
            MO["One mass function per source<br/>A: {Flu} 0.80; {Flu, COVID} 0.20<br/>B: {COVID} 0.50; {Flu, COVID} 0.50"]
            MI --> MP --> MO
        end

        subgraph DST_IO["4 · Combine evidence"]
            direction LR
            DI["All source mass functions<br/>A's masses + B's masses"]
            DP["DST · Dempster's rule<br/>Fuse evidence and quantify conflict"]
            DO["Combined masses<br/>{Flu}: 66.7%<br/>{COVID}: 16.7%<br/>{Flu, COVID}: 16.7%"]
            DK["Conflict: 40%"]
            DI --> DP --> DO
            DP --> DK
        end

        FRAME_IO --> FOCAL_IO --> MASS_IO --> DST_IO
    end

    GO -->|Source responses| HI

    classDef data fill:#F1F5F9,stroke:#64748B,color:#0F172A
    classDef llm fill:#DBEAFE,stroke:#3B82F6,color:#1E3A8A
    classDef dst fill:#D1FAE5,stroke:#10B981,color:#064E3B
    classDef conflict fill:#FEE2E2,stroke:#DC2626,color:#B91C1C

    class GI,GO,HI,HO,FI,FO,MI,MO,DI data
    class GP,HP,FP,MP llm
    class DP,DO dst
    class DK conflict
```

[Standalone diagram source](diagrams/pipeline-inputs-outputs.mmd)
