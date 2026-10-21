#!/usr/bin/env python3
"""Unit tests of the event rules (e_events.py) and the formal judgment levels
(e_eval_test.level) on constructed inputs. Writes validation/events_checks.json."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e_common  # noqa: F401,E402
from e_eval_test import level  # noqa: E402
from e_events import NOT_HAPPENED, consistency, first_sustained, relation  # noqa: E402

S = [0, 25, 50, 75, 100]
cases = {
    "single_blip_not_an_event": first_sustained(S, {0: False, 25: True, 50: False, 75: True, 100: True}) == 75,
    "last_checkpoint_needs_no_successor": first_sustained(S, {0: False, 25: False, 50: False, 75: False, 100: True}) == 100,
    "missing_successor_blocks": first_sustained(S, {0: False, 25: True, 50: None, 75: False, 100: False}) == NOT_HAPPENED,
    "never": first_sustained(S, {s: False for s in S}) == NOT_HAPPENED,
    "relation_earlier": relation(25, 75, S) == "早于",
    "relation_same": relation(50, 50, S) == "同时",
    "relation_later": relation(100, 25, S) == "晚于",
    "relation_one_missing": relation(NOT_HAPPENED, 25, S) == "前者未发生",
    "consistent_5": consistency({i: "早于" for i in range(5)}, 2)["label"] == "一致",
    "majority_4_of_5": consistency({0: "早于", 1: "早于", 2: "早于", 3: "早于", 4: "同时"}, 2)["label"] == "多数",
    "inconsistent_3_of_5": consistency({0: "早于", 1: "早于", 2: "早于", 3: "同时", 4: "晚于"}, 2)["label"] == "不一致",
    "bridge_2_of_3_inconsistent": consistency({0: "早于", 1: "早于", 2: "同时"}, 4)["label"] == "不一致",
    "level_learned": level(0.95, 0.93, 0.85, 0.9, 0.05) == "学会",
    "level_sign": level(0.6, 0.55, 0.3, 0.3, 0.7) == "出现学习迹象",
    "level_ci_at_50_not_sign": level(0.52, 0.499, 0.1, 0.1, 0.5) == "未满足综合学习迹象标准",
    "level_insensitive_not_sign": level(0.7, 0.65, 0.3, 0.4, 0.92) == "未满足综合学习迹象标准",
    "level_high_acc_low_rs": level(0.95, 0.93, 0.7, 0.9, 0.05) == "出现学习迹象",
}
out = {"cases": cases, "pass": all(cases.values())}
with open(os.path.join(HERE, "validation", "events_checks.json"), "w") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
sys.exit(0 if out["pass"] else 1)
