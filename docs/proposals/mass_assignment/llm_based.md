# Assigning belief masses to source responses

In this project, each source response should become a **basic belief assignment** (BBA), also called a **mass function**, over the extracted frame of discernment.

The repository already models:

- each source as a `ModelOutput` containing `source` and free-text `response`; and
- the universe of discourse as a `FrameOfDiscernment` containing elementary hypothesis labels. src/concerted_abduction/types.py:10-18src/concerted_abduction/types.py:55-60

However, mass assignment is currently only planned: the mass-function package and implementation do not yet exist. docs/architecture.md:40-44docs/roadmap.md:14-18

## 1. Mathematical definition

Let the extracted frame be

\[
\Theta=\{\theta_1,\theta_2,\ldots,\theta_n\}.
\]

For each source \(s\), construct a mass function

\[
m_s:2^\Theta\rightarrow[0,1],
\]

subject to

\[
m_s(\varnothing)=0,
\qquad
\sum_{A\subseteq\Theta}m_s(A)=1.
\]

A subset \(A\) with \(m_s(A)>0\) is a **focal set**.

The important distinction from ordinary multiclass probabilities is that mass may be assigned directly to a set:

\[
m_s(\{\theta_1,\theta_2\})=0.7.
\]

This means that the response supports “either \(\theta_1\) or \(\theta_2\), without enough evidence to distinguish them.” It does **not** mean that each hypothesis receives \(0.35\). This ability to represent unresolved alternatives is precisely why the repository proposes DST rather than simple voting or averaging. docs/overview.md:13-17

---

## 2. Recommended assignment procedure

Use four separate stages:

1. **Map the response to hypotheses.**
2. **Measure the strength of support for each claim.**
3. **Estimate the reliability of the source.**
4. **Reserve unsupported mass for ignorance.**

Do not ask the current hypothesis extractor to assign masses. Its prompt explicitly says to return only elementary, canonical hypotheses and not to rank them or assign probabilities or belief masses. prompts/extractors/hypothesis/v0.txt:5-12

### Stage A: Extract source-specific claims

For every source response, map each relevant statement to one of:

- a singleton \(\{\theta_i\}\), when it clearly supports one hypothesis;
- a composite set \(\{\theta_i,\theta_j,\ldots\}\), when it leaves several hypotheses unresolved;
- the full frame \(\Theta\), for residual ignorance;
- optionally, a negative proposition such as \(\Theta\setminus\{\theta_i\}\), when the source explicitly rules out \(\theta_i\).

For example, suppose:

\[
\Theta=
\{
\text{eye strain},
\text{tension headache},
\text{refractive error}
\}.
\]

A response saying:

> Eye strain is most likely, although refractive error cannot be excluded.

could initially produce:

\[
w(\{\text{eye strain}\})=0.75,
\]

\[
w(\{\text{eye strain},\text{refractive error}\})=0.20,
\]

with the remaining \(0.05\) assigned to \(\Theta\).

The composite set preserves the source’s linguistic uncertainty instead of forcing it into an artificial singleton probability.

### Stage B: Convert linguistic strength into provisional support

Use a documented calibration table rather than letting an LLM invent unconstrained numbers for every response.

A reasonable initial scale is:

| Linguistic expression | Provisional support |
|---|---:|
| “certain,” “diagnostic of” | 0.90–0.98 |
| “very likely,” “strongly suggests” | 0.75–0.90 |
| “likely,” “most consistent with” | 0.60–0.75 |
| “possible,” “may be” | 0.30–0.55 |
| “cannot exclude” | 0.10–0.30 |
| merely mentioned | 0.05–0.15 |

These are **calibration parameters**, not universal mathematical constants. Ideally, learn or validate them against a labeled development set.

Also incorporate:

- specificity of the claim;
- amount of supporting evidence stated in the response;
- contradictions within the response;
- hedging and epistemic modality;
- whether the response is proposing or merely discussing a hypothesis;
- whether it explicitly rules out a hypothesis.

A practical scoring model is

\[
z_{s,A}
=
\beta_0
+\beta_1L_{s,A}
+\beta_2E_{s,A}
-\beta_3H_{s,A}
-\beta_4C_{s,A},
\]

where:

- \(L\) is linguistic commitment;
- \(E\) is evidence or rationale strength;
- \(H\) is hedging;
- \(C\) is contradiction or inconsistency.

Convert it to a bounded support score with

\[
q_{s,A}=\sigma(z_{s,A})
       =\frac{1}{1+e^{-z_{s,A}}}.
\]

If you do not yet have labeled data for estimating the \(\beta\) coefficients, start with a transparent rule-based scale and report it as heuristic.

### Stage C: Normalize claim support

If the source supports focal sets \(A_1,\ldots,A_k\), normalize their provisional weights:

\[
\widetilde m_s(A_i)
=
\frac{w_{s,i}}
{\sum_{j=1}^{k}w_{s,j}}.
\]

This produces a provisional mass function representing what the response says, before accounting for whether the source itself should be trusted.

Do **not** independently assign a confidence in \([0,1]\) to every hypothesis and then treat those values as masses unless they sum to at most one. Independent confidence scores are not automatically a valid BBA.

---

## 3. Discount the masses by source reliability

Distinguish two different concepts:

- **claim confidence**: how strongly the response endorses a proposition;
- **source reliability**: how trustworthy or well-calibrated the responding model is.

Let the source reliability be

\[
r_s\in[0,1].
\]

Apply standard reliability discounting:

\[
m_s(A)=r_s\widetilde m_s(A),
\qquad
A\neq\Theta,
\]

and

\[
m_s(\Theta)
=
1-r_s+r_s\widetilde m_s(\Theta).
\]

Thus, unreliability becomes **ignorance**, rather than support for a competing hypothesis.

For example, suppose the response-level assignment is

\[
\widetilde m_s(\{\theta_1\})=0.70,
\]

\[
\widetilde m_s(\{\theta_1,\theta_2\})=0.20,
\]

\[
\widetilde m_s(\Theta)=0.10,
\]

and source reliability is \(r_s=0.8\). Then:

\[
m_s(\{\theta_1\})=0.8(0.70)=0.56,
\]

\[
m_s(\{\theta_1,\theta_2\})=0.8(0.20)=0.16,
\]

\[
m_s(\Theta)
=
1-0.8+0.8(0.10)
=
0.28.
\]

The result sums to one:

\[
0.56+0.16+0.28=1.
\]

### Estimating \(r_s\)

Prefer empirical calibration using held-out labeled examples. Suitable signals include:

- diagnostic accuracy;
- Brier score or log loss;
- expected calibration error;
- factuality or hallucination rate;
- domain-specific competence;
- stability across equivalent prompts;
- known provenance or model version.

Avoid deriving source reliability merely from whether that source agrees with the other sources. Otherwise correlated models can reinforce the same shared error.

---

## 4. A good baseline for this repository

For an initial, interpretable implementation, I recommend the following policy:

### If the source names one clear hypothesis

For support strength \(c_s\),

\[
m_s(\{\theta_i\})=r_sc_s,
\]

\[
m_s(\Theta)=1-r_sc_s.
\]

### If the source genuinely cannot distinguish several hypotheses

For \(A=\{\theta_i,\theta_j,\ldots\}\),

\[
m_s(A)=r_sc_s,
\]

\[
m_s(\Theta)=1-r_sc_s.
\]

### If the response ranks several distinct hypotheses

Let \(w_1,\ldots,w_k\geq0\) encode the response’s relative support and let \(c_s\) be its overall committed mass:

\[
m_s(A_i)
=
r_sc_s
\frac{w_i}{\sum_jw_j},
\]

\[
m_s(\Theta)=1-r_sc_s.
\]

This intentionally leaves all uncommitted support on the complete frame.

### If the response contains no usable evidence

Use the vacuous mass function:

\[
m_s(\Theta)=1.
\]

This says “the source provides no discriminating evidence,” which is different from assigning equal singleton probabilities.

---

## 5. Worked example

Suppose:

\[
\Theta=\{A,B,C\}.
\]

Source 1 says:

> A is most likely; B remains possible.

Choose the provisional response masses:

\[
\widetilde m_1(\{A\})=0.65,
\]

\[
\widetilde m_1(\{A,B\})=0.25,
\]

\[
\widetilde m_1(\Theta)=0.10.
\]

If \(r_1=0.9\), discount them:

\[
m_1(\{A\})=0.585,
\]

\[
m_1(\{A,B\})=0.225,
\]

\[
m_1(\Theta)=0.19.
\]

Source 2 says:

> The evidence is compatible with either B or C; I cannot distinguish them.

A suitable assignment is:

\[
\widetilde m_2(\{B,C\})=0.75,
\qquad
\widetilde m_2(\Theta)=0.25.
\]

If \(r_2=0.7\):

\[
m_2(\{B,C\})=0.525,
\]

\[
m_2(\Theta)=0.475.
\]

Notice that Source 2’s \(0.525\) is assigned to the set \(\{B,C\}\), not divided between \(B\) and \(C\). Splitting it would claim information the response did not provide.

---

## 6. Belief and plausibility after mass assignment

For any proposition \(A\subseteq\Theta\), calculate:

\[
\operatorname{Bel}_s(A)
=
\sum_{B\subseteq A}m_s(B),
\]

and

\[
\operatorname{Pl}_s(A)
=
\sum_{B\cap A\neq\varnothing}m_s(B)
=
1-\operatorname{Bel}_s(\overline A).
\]

The interval

\[
[\operatorname{Bel}_s(A),\operatorname{Pl}_s(A)]
\]

represents lower and upper support for \(A\).

For Source 1 above:

\[
\operatorname{Bel}_1(\{A\})=0.585,
\]

while

\[
\operatorname{Pl}_1(\{A\})
=
0.585+0.225+0.19
=
1.
\]

Thus, direct confirmed support for \(A\) is \(0.585\), but none of the remaining mass rules \(A\) out.

---

## 7. Important modeling cautions

### Do not confuse sets with distributions

\[
m(\{A,B\})=0.6
\]

is not equivalent to

\[
m(\{A\})=0.3,\qquad m(\{B\})=0.3.
\]

The first expresses unresolved ambiguity; the second makes separate commitments.

### Do not force all remaining mass onto mentioned alternatives

Put uncommitted mass on \(\Theta\). This preserves epistemic ignorance.

### Do not use response length as confidence

A verbose response is not necessarily better supported or more reliable.

### Treat exclusions carefully

“Less likely” is not the same as “ruled out.” Only assign mass to a complement such as \(\Theta\setminus\{A\}\) when the source clearly provides negative evidence against \(A\).

### Account for dependence before combination

Dempster’s rule assumes sufficiently distinct evidence sources. LLMs may share training data, architecture, prompts, retrieval material, or systematic biases. Treating correlated outputs as independent can substantially overstate belief.

### Keep mass extraction auditable

If an LLM performs the semantic mapping, have it return structured intermediate information:

- focal set;
- supporting quotation or span;
- linguistic commitment label;
- rationale;
- provisional score;
- source reliability;
- final discounted mass.

Then validate the mathematical constraints programmatically.

---

## 8. Recommended structured representation

A source mass function could be represented as:

```json
{
  "source": "Model A",
  "frame": [
    "eye strain",
    "tension headache",
    "refractive error"
  ],
  "reliability": 0.8,
  "focal_sets": [
    {
      "hypotheses": ["eye strain"],
      "mass": 0.56
    },
    {
      "hypotheses": ["eye strain", "refractive error"],
      "mass": 0.16
    },
    {
      "hypotheses": [
        "eye strain",
        "tension headache",
        "refractive error"
      ],
      "mass": 0.28
    }
  ]
}
```

Validate that:

```python
assert all(0.0 <= focal.mass <= 1.0 for focal in focal_sets)
assert abs(sum(focal.mass for focal in focal_sets) - 1.0) < 1e-9
assert not any(len(focal.hypotheses) == 0 for focal in focal_sets)
assert all(set(focal.hypotheses) <= set(frame) for focal in focal_sets)
```

This aligns with the repository’s intended next stage: taking each model response and the extracted universe of discourse and producing a confidence-weighted mass distribution over subsets. docs/architecture.md:40-44

## Bottom line

The safest initial design is:

\[
\boxed{
\text{response semantics}
\rightarrow
\text{focal sets}
\rightarrow
\text{provisional support}
\rightarrow
\text{reliability discounting}
\rightarrow
\text{residual mass on }\Theta
}
\]

Start with transparent linguistic rules, calibrate them on labeled data, preserve ambiguity with composite focal sets, and use the full frame for ignorance. Only after producing one valid mass function per source should the system combine them using Dempster’s rule—the combination stage is also still unimplemented in the current repository. docs/architecture.md:46-50

## Repository checks used

* ✅ `pwd && printf '%s\n' '--- AGENTS ---' && find .. -name AGENTS.md -print && printf '%s\n' '--- FILES ---' && rg --files -g '!**/.git/**' | sed -n '1,160p'`
* ✅ `rg -n -i "belief|mass|source response|response|dempster|shafer|confidence|reliab|hypothes" README.md docs src scripts todo.md prompts data/synthetic/examples/common_input/v0.json`
* ✅ `nl -ba docs/overview.md | sed -n '9,18p'; printf '\n--- architecture ---\n'; nl -ba docs/architecture.md | sed -n '29,52p'; printf '\n--- types ---\n'; nl -ba src/concerted_abduction/types.py | sed -n '1,75p'; printf '\n--- roadmap ---\n'; nl -ba docs/roadmap.md | sed -n '12,20p'; printf '\n--- prompt ---\n'; nl -ba prompts/extractors/hypothesis/v0.txt | sed -n '1,22p'`

No repository files were changed, so there was no commit or pull request to create.