"""Standard-library-only aggregation of the frozen 84-row decoding review.

No model, tokenizer, sampling, file writes, or inference occurs in this module.
An assessment PASS means complete review evidence, not language-quality success.
Policy/panel quality_status fields carry the actual quality-screen decisions.
"""

from collections.abc import Mapping


POLICY_PANELS = {"G": (0,), "S": (1, 2, 3), "P": (1, 2, 3)}
REQUIRED_FIELDS = ("id", "policy", "panel", "auto_pass", "review_a", "review_b")
PROMPT_IDS = tuple(range(1, 13))
REQUIRED_JOINT = 9
EXPECTED_ROWS = 84


def summarize_quality(rows):
    """Summarize all 84 prescribed rows without imputing missing outcomes.

    Rows require integer IDs, policy G/S/P, the prescribed integer panel,
    Boolean auto_pass, and Boolean-or-None independent review_a/review_b labels.
    Structural defects return BLOCKED. Explicit pending labels return NOT TESTED.
    A completed panel passes iff >=9 of its 12 rows pass auto and BOTH reviews.
    S/P pass iff all three completed panels pass. G is a separate reference.
    Counts on incomplete evidence are descriptive and marked incomplete.
    """
    errors = []
    panel_errors = {(policy, panel): [] for policy, panels in POLICY_PANELS.items()
                    for panel in panels}
    buckets = {(policy, panel, idx): [] for policy, panels in POLICY_PANELS.items()
               for panel in panels for idx in PROMPT_IDS}

    def issue(reason, index=None, policy=None, panel=None, prompt_id=None):
        item = {"reason": reason}
        if index is not None:
            item["row_index"] = index
        if policy is not None:
            item["policy"] = policy
        if panel is not None:
            item["panel"] = panel
        if prompt_id is not None:
            item["id"] = prompt_id
        errors.append(item)
        if (policy, panel) in panel_errors:
            panel_errors[(policy, panel)].append(item)

    if not isinstance(rows, list):
        issue("rows must be a list")
        supplied_rows = []
        supplied_count = None
    else:
        supplied_rows = rows
        supplied_count = len(rows)

    for index, row in enumerate(supplied_rows):
        if not isinstance(row, Mapping):
            issue("row must be an object", index=index)
            continue
        policy, panel, idx = row.get("policy"), row.get("panel"), row.get("id")
        if not isinstance(policy, str) or policy not in POLICY_PANELS:
            issue("policy must be G, S, or P", index=index)
            continue
        if type(panel) is not int or panel not in POLICY_PANELS[policy]:
            issue("panel differs from the frozen policy panels", index=index, policy=policy)
            continue
        if type(idx) is not int or idx not in PROMPT_IDS:
            issue("prompt ID must be an integer from 1 through 12", index=index,
                  policy=policy, panel=panel)
            continue
        valid = True
        if any(field not in row for field in REQUIRED_FIELDS):
            issue("required row field is missing", index=index, policy=policy, panel=panel, prompt_id=idx)
            valid = False
        if type(row.get("auto_pass")) is not bool:
            issue("auto_pass must be Boolean", index=index, policy=policy, panel=panel, prompt_id=idx)
            valid = False
        for field in ("review_a", "review_b"):
            value = row.get(field)
            if value is not None and type(value) is not bool:
                issue(field + " must be Boolean or explicit null", index=index,
                      policy=policy, panel=panel, prompt_id=idx)
                valid = False
        normalized = ({field: row[field] for field in REQUIRED_FIELDS} if valid else None)
        buckets[(policy, panel, idx)].append({"row_index": index, "row": normalized})

    for (policy, panel, idx), entries in buckets.items():
        if not entries:
            issue("planned output row is missing", policy=policy, panel=panel, prompt_id=idx)
        elif len(entries) != 1:
            issue("duplicate planned output identity", policy=policy, panel=panel, prompt_id=idx)

    policies = {}
    for policy, expected_panels in POLICY_PANELS.items():
        panel_reports = []
        valid_by_panel = {}
        for panel in expected_panels:
            valid_rows = [entries[0]["row"] for idx in PROMPT_IDS
                          if len(entries := buckets[(policy, panel, idx)]) == 1
                          and entries[0]["row"] is not None]
            valid_by_panel[panel] = {row["id"]: row for row in valid_rows}
            reviewed = [row for row in valid_rows if row["review_a"] is not None
                        and row["review_b"] is not None]
            auto_ids = [row["id"] for row in valid_rows if row["auto_pass"]]
            both_ids = [row["id"] for row in reviewed
                        if row["review_a"] is True and row["review_b"] is True]
            joint_ids = [row["id"] for row in reviewed if row["auto_pass"]
                         and row["review_a"] is True and row["review_b"] is True]
            disagreements = [row["id"] for row in reviewed
                             if row["review_a"] != row["review_b"]]
            complete = not panel_errors[(policy, panel)] and len(reviewed) == 12
            if panel_errors[(policy, panel)]:
                quality_status = "BLOCKED"
            elif not complete:
                quality_status = "NOT TESTED"
            else:
                quality_status = "PASS" if len(joint_ids) >= REQUIRED_JOINT else "FAIL"
            panel_reports.append({
                "panel": panel, "quality_status": quality_status,
                "expected_rows": 12, "valid_unique_rows": len(valid_rows),
                "reviewed_rows": len(reviewed), "counts_complete": complete,
                "automatic_pass_count": len(auto_ids), "automatic_pass_ids": auto_ids,
                "review_a_true_count": sum(row["review_a"] is True for row in valid_rows),
                "review_b_true_count": sum(row["review_b"] is True for row in valid_rows),
                "coherent_both_count": len(both_ids), "coherent_both_ids": both_ids,
                "joint_pass_count": len(joint_ids), "joint_pass_ids": joint_ids,
                "disagreement_count": len(disagreements), "disagreement_ids": disagreements,
                "required_joint_pass_count": REQUIRED_JOINT,
                "errors": panel_errors[(policy, panel)],
            })
        statuses = [panel["quality_status"] for panel in panel_reports]
        if "BLOCKED" in statuses:
            quality_status = "BLOCKED"
        elif "NOT TESTED" in statuses:
            quality_status = "NOT TESTED"
        else:
            quality_status = "PASS" if all(value == "PASS" for value in statuses) else "FAIL"
        complete = all(panel["counts_complete"] for panel in panel_reports)
        prompt_repeats = []
        for idx in PROMPT_IDS:
            observations = [valid_by_panel[panel].get(idx) for panel in expected_panels]
            rated = [row for row in observations if row is not None
                     and row["review_a"] is not None and row["review_b"] is not None]
            prompt_repeats.append({
                "id": idx, "planned_repeats": len(expected_panels), "reviewed_repeats": len(rated),
                "joint_pass_repeats": sum(row["auto_pass"] and row["review_a"] is True
                                          and row["review_b"] is True for row in rated),
                "descriptive_only": True,
            })
        policies[policy] = {
            "role": {"G": "reference", "S": "primary", "P": "secondary"}[policy],
            "quality_status": quality_status,
            "expected_panels": list(expected_panels), "expected_rows": 12 * len(expected_panels),
            "panels": panel_reports, "counts_complete": complete,
            "joint_counts_by_panel": {str(panel["panel"]): panel["joint_pass_count"] for panel in panel_reports},
            "minimum_joint_count": min(panel["joint_pass_count"] for panel in panel_reports) if complete else None,
            "pooled_joint_count_descriptive": sum(panel["joint_pass_count"] for panel in panel_reports),
            "per_prompt_repeats_descriptive": prompt_repeats,
            "majority_rule_used": False,
            "acceptance_rule": "Every prescribed panel separately has at least 9 of 12 auto-and-both-review passes",
        }

    input_status = "BLOCKED" if errors else "PASS"
    all_reviewed = all(policy["counts_complete"] for policy in policies.values())
    assessment_status = "BLOCKED" if errors else "PASS" if all_reviewed else "NOT TESTED"
    return {
        "assessment_status": assessment_status, "input_status": input_status,
        "assessment_status_is_language_verdict": False,
        "expected_rows": EXPECTED_ROWS, "supplied_rows": supplied_count,
        "errors": errors, "policies": policies,
        "primary_quality_status": "BLOCKED" if errors else policies["S"]["quality_status"],
        "secondary_quality_status": "BLOCKED" if errors else policies["P"]["quality_status"],
        "reference_quality_status": "BLOCKED" if errors else policies["G"]["quality_status"],
        "complete_matrix_decisions_available": assessment_status == "PASS",
        "sample_scope": "12 previously viewed development prompts; no fresh-test or statistical confirmation",
        "factual_and_code_correctness": "Separate descriptive review, not inferred from these Boolean labels",
    }
