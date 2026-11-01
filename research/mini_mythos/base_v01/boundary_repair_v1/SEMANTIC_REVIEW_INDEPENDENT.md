# Independent source-boundary review

Purpose: Review every supplied boundary candidate and the wider block-start inventory for the data-only repair. Determine source article boundaries from structure and surrounding meaning, without model scores, token selection or model execution.

Environment: Local read-only JSON inspection using PowerShell. No parser implementation, Torch, model, tokenizer or experiment was imported or executed. Only this summary document was written.

Input: `REVIEW_INVENTORY_EXTERNAL.json`, 488,268 bytes, SHA-256 `06de01527637acc698d922179142f1eea1324fdb63c8abd0afcc513f0494f4a4`. It reports the pinned 4,358-row corpus SHA-256 `3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925` and row-vector SHA-256 `8a970098c794df2d25494abf3caf6cb8499f57cc54bca35e45b70e168f7d9a74`.

Expected: Individually assess all 66 top-level/other contexts, all 644 nested titles, and all 1,320 supplied block-start previews. Report accepted boundaries, rejected candidates and unresolved cases. Do not infer article identity from different content hashes or force a predetermined article count.

Actual: All supplied inventories were read. The 710 unique broad candidates comprise 60 accepted article boundaries, two rejected formula continuations, four rejected annotation continuations and 644 nested section titles. All 644 nested titles have balanced levels of at least two and are retained within their source article. All 1,320 block-start previews were covered: 704 repeat already-reviewed article/section headings and 616 are non-heading starts. No additional article boundary or unresolved candidate was identified within this supplied review material.

Status: **PASS for the scoped semantic review and the boundary labels below.** This is not an implementation/test verdict, a full independent Parquet extraction, or a scientific-model result.

## Accepted article heading rows

These are zero-based source row numbers. Acceptance used the title together with the supplied article introduction and context, not just the blank-line pattern. The resulting count is 60; it was not used as an acceptance target.

```text
1, 32, 116, 177, 264, 295, 322, 447, 530, 704,
734, 789, 930, 954, 991, 1009, 1085, 1200, 1223, 1265,
1319, 1382, 1430, 1496, 1652, 1731, 1833, 2093, 2159, 2227,
2249, 2315, 2342, 2441, 2565, 2594, 2726, 2789, 2991, 3218,
3265, 3296, 3355, 3399, 3426, 3454, 3614, 3636, 3666, 3722,
3768, 3825, 3841, 3863, 3884, 4011, 4024, 4122, 4224, 4303
```

The source-article identity must bind the pinned corpus, this reviewed heading row and its title. Article body spans are the original rows after each accepted heading up to, but excluding, the next accepted heading; the final span ends at the corpus end. This describes the expected mapping, not a claim that a new implementation has already verified its bytes.

## Rejected top-level and other candidates

| Source row | Decision and reason | Source article heading row |
|---|---|---:|
| 2148 | Body: continuation of a filter-frequency/impedance expression across adjacent prose rows. It is neither a new subject nor an article introduction. | 2093 |
| 2150 | Body: continuation of the same filter example, joining the preceding inductance wording to the following capacitance value. | 2093 |
| 3416 | Body: qualification-status explanation in an athletics legend, immediately following its symbol. | 3399 |
| 3417 | Body: a further qualification symbol and equality marker in that legend. | 3399 |
| 3420 | Body: national-record explanation paired with the preceding abbreviation. | 3399 |
| 3421 | Body: not-applicable symbol and equality marker paired with the following explanation. | 3399 |

All six must remain in the unmodified source body. They must not be deleted or converted into titles. The 644 nested headings remain body rows as well.

## Broader scan and limits

The wider scan included prose introductions, paragraph continuations, lists, credits, legends and short non-marked labels. Such short entries as club names, list labels and related-link titles are supported by their surrounding article/section organization and did not require a new article boundary. The supplied contexts and previews raised no additional unresolved boundary decision.

This review examined all material present in the review pack: full candidate/section titles, the supplied neighboring/following context, and the supplied block previews of up to 240 characters. It did not read every full body row beyond those excerpts or independently recreate this pack from Parquet. Completeness and byte preservation of the pack and resulting ledger therefore still require the separate source-bound audit. A claim that every original body sentence was independently read would be incorrect.

The reviewer knew the previously identified formula defect and had participated in the earlier protocol review. This is a separate reviewer judgment from the new parser implementation, not an independent human ground truth or a blind review of the known defect. No V1 model-score files were consulted in this data review.

Blank isolation plus top-level syntax is useful for this artifact, but is not a universal semantic proof: a blank-isolated formula can look like a title. General-rule fixtures must retain that ambiguity and require a reviewed decision rather than silently accepting it. Any disagreement between the reviewed ledger, source-bound inventory or implementation remains BLOCKED until resolved.

This review does not revise V1, select a replacement sample, regroup its bootstrap, or retroactively accept its article-level inference. Further numerical research remains outside this data-only stage.
