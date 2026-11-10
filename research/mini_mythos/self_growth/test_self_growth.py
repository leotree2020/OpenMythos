"""Tests for the self-growth pilot that need no model (CPU, standard library only).

  python -B -m unittest test_self_growth -v
"""
import collections
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import world as W  # noqa: E402


def solve(world, q):
    """Answer a question from the structured facts only (independent of how the question was built)."""
    p = q["subject"]
    t = q["type"]
    if t == "R1":
        return world["craft"][p]
    if t == "R2":
        return world["trainer"][p]
    if t == "R3":
        return world["town"][p]
    if t == "I1":
        return world["guild_of_craft"][world["craft"][p]]
    m = world["trainer"][p]
    return world["town"][m] if t == "C1" else world["guild_of_craft"][world["craft"][m]]


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.w = W.build(seed=100)

    def test_deterministic_and_different_per_seed(self):
        self.assertEqual(W.build(seed=100), self.w)
        other = W.build(seed=0)
        self.assertNotEqual(other["persons"], self.w["persons"])
        self.assertNotEqual(other["trainer"], self.w["trainer"])

    def test_sizes_and_balance(self):
        w = self.w
        self.assertEqual(len(w["persons"]), 32)
        self.assertEqual(len(set(w["persons"])), 32)
        self.assertEqual(len(w["seeds"]), 32 + 32 + 24)
        kinds = collections.Counter(s["kind"] for s in w["seeds"])
        self.assertEqual(kinds, {"K1": 32, "K3": 32, "K2": 24})
        types = collections.Counter(q["type"] for q in w["questions"])
        self.assertEqual(types, {"R1": 32, "R3": 32, "I1": 32, "R2": 24, "C1": 24, "C2": 24})
        self.assertEqual(set(collections.Counter(w["craft"].values()).values()), {4})     # every craft 4 people
        self.assertEqual(set(collections.Counter(w["town"].values()).values()), {4})
        for t in W.QUESTION_TYPES:                           # the correct letter is balanced within each type
            pos = collections.Counter(q["answer"] for q in w["questions"] if q["type"] == t)
            self.assertLessEqual(max(pos.values()) - min(pos.values()), 1, t)
            self.assertEqual(len(pos), 4, t)

    def test_answers_follow_from_the_facts(self):
        for seed in (0, 100, 7):
            w = W.build(seed=seed)
            for q in w["questions"]:
                self.assertEqual(len(q["options"]), 4)
                self.assertEqual(len(set(q["options"])), 4, q)
                self.assertEqual(q["options"][q["answer"]], solve(w, q), q)

    def test_trainers_differ_from_learners(self):
        w = self.w
        for p, m in w["trainer"].items():
            self.assertNotEqual(p, m)
            self.assertNotEqual(w["town"][p], w["town"][m])
            self.assertNotEqual(w["guild"][p], w["guild"][m])
            self.assertNotEqual(w["trainer"].get(m), p)                      # nobody trains their own trainer
        for q in w["questions"]:                           # answering about P itself is a wrong option
            if q["type"] == "C1":
                self.assertIn(w["town"][q["subject"]], q["options"])
                self.assertNotEqual(q["options"][q["answer"]], w["town"][q["subject"]])
            if q["type"] == "C2":
                self.assertIn(w["guild"][q["subject"]], q["options"])
                self.assertNotEqual(q["options"][q["answer"]], w["guild"][q["subject"]])

    def test_seeds_state_what_recall_needs_and_not_the_combined_facts(self):
        w = self.w
        by_id = {s["id"]: s for s in w["seeds"]}
        for q in w["questions"]:
            texts = [by_id[i]["text"] for i in q["needs"]]
            answer = q["options"][q["answer"]]
            self.assertTrue(any(answer in t for t in texts), q)             # the answer is in the needed seeds
            if q["type"] in ("C1", "C2"):
                self.assertEqual(len(q["needs"]), 2)
                for s in w["seeds"]:                        # no single seed names the learner and the answer
                    core = answer.replace("Guild of the ", "")
                    self.assertFalse(q["subject"] in s["text"] and core in s["text"], (q, s))

    def test_prompts(self):
        w = self.w
        q = next(x for x in w["questions"] if x["type"] == "C1")
        closed = W.closed_book_prompt(q)
        self.assertIn(q["question"], closed)
        self.assertNotIn("trained by", closed)              # no facts in the closed-book prompt
        for line, opt in zip(closed.splitlines()[2:6], q["options"]):
            self.assertTrue(line.endswith(opt))
        opened = W.open_book_prompt(w, q)
        by_id = {s["id"]: s for s in w["seeds"]}
        for i in q["needs"]:
            self.assertIn(by_id[i]["text"], opened)
        self.assertEqual(opened.count("\n- "), 2 + 4)       # two needed seeds + four unrelated ones
        self.assertEqual(W.open_book_prompt(w, q), opened)  # fixed order
        for text in (W.derive_prompt("X."), W.connect_prompt("X.", "Y.")):
            self.assertNotIn("guild", text.lower())         # the prompts name no question and no answer
            self.assertNotIn("town", text.lower())


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.w = W.build(seed=100)

    def test_clean_lines(self):
        self.assertEqual(W.clean_lines("1. First.\n\n- Second.\n  3) Third. \n"), ["First.", "Second.", "Third."])

    def test_statement_checks(self):
        w = self.w
        p, m = next(iter(w["trainer"].items()))
        g, gm = w["guild"][p], w["guild"][m]
        self.assertTrue(W.states_guild("%s is sworn to the %s." % (p, g), w, p))
        self.assertFalse(W.states_guild("In Veltar, every %s is sworn to the %s. %s is a %s." % (
            w["craft"][p], g, p, w["craft"][p]), w, p))                      # the seed restated does not count
        self.assertFalse(W.states_guild("%s is a %s." % (p, w["craft"][p]), w, p))
        self.assertTrue(W.states_trainer_town("%s was trained by someone born in %s." % (p, w["town"][m]), w, p))
        self.assertFalse(W.states_trainer_town("%s was born in the town of %s." % (m, w["town"][m]), w, p))
        self.assertTrue(W.states_trainer_guild("%s's trainer is sworn to the %s." % (p, gm), w, p))
        # consistency: a town or guild must belong to someone named in the line
        self.assertTrue(W.consistent("%s was born in %s." % (p, w["town"][p]), w))
        self.assertTrue(W.consistent("%s was trained by %s, who was born in %s." % (p, m, w["town"][m]), w))
        self.assertFalse(W.consistent("%s was born in %s." % (p, w["town"][m]), w))
        self.assertFalse(W.consistent("%s is sworn to the %s." % (p, gm), w))
        self.assertTrue(W.consistent("Every %s is sworn to the %s." % (w["craft"][p], g), w))   # names nobody

    def test_pairs(self):
        w = self.w
        linked = W.linked_pairs(w)
        self.assertEqual(len(linked), 24)
        for p, a, b in linked:
            self.assertEqual((a["kind"], b["kind"]), ("K2", "K3"))
            self.assertEqual(a["persons"], [p, w["trainer"][p]])
            self.assertEqual(b["persons"], [w["trainer"][p]])
        for a, b in W.unlinked_pairs(w, 10):
            self.assertFalse(set(a["persons"]) & set(b["persons"]))
        self.assertEqual(W.unlinked_pairs(w, 10), W.unlinked_pairs(w, 10))


if __name__ == "__main__":
    unittest.main()
