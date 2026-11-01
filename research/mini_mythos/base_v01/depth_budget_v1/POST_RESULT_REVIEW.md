# Independent internal review of source-unit failure

Reviewer: separate internal ChatGPT agent, read-only. No model execution or edits; not Claude/Grok/human/third-party review.

The reviewer checked prepare_inputs.py lines24–38 and PROTOCOL's frozen header rule. They agree: stripped rows starting and ending with '=' and containing exactly two '=' are treated as top-level titles. Execution followed the rule; the rule has a semantic defect.

The raw external source-boundary evidence is6136 bytes, SHA256 `81fa53b50fe89de58ae7b665a18c9031ad6c3a707ca88b4dae4118d53d2fb04e`. Its original corpus context shows row2150 is a formula continuation about inductance/capacitance, not a new article. Row2148 is another false-title candidate. Row2093 is the actual Constant k filter title. The selected units0 and3 therefore cannot be treated as distinct source articles.

Verdict: source-unit semantic integrity FAIL. Retain computational audit PASS within its scope and all original results. Retain point estimates as conditional descriptions of32 selected segments, but reject the32-independent-article bootstrap interpretation. Do not claim31 actual articles or exactly60 source articles without a separate complete boundary audit. Do not drop, regroup, recalculate alternative estimates or rerun the model in this stage.

Next stage: a separately registered data-only audit of all candidate boundaries, followed by a general rule correction and fixtures. Model scores must not determine which source rows are excluded. Raw corpus excerpts remain external; publish only this summary and the exact evidence hash.
