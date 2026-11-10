"""Self-growth pilot: an invented world ("Veltar") whose knowledge a model cannot have seen, with
questions that have exact answers. Everything is generated from one integer seed.

Seeds (short pieces of knowledge, one or two sentences each):
  K1  "In Veltar, every <craft> is sworn to the <guild>. <P> is a <craft>."   (a rule and an instance)
  K2  "In Veltar, <P> was trained by <M>."
  K3  "In Veltar, <P> was born in the town of <town>."

Questions (four options, one correct; chance = 25%):
  R1  What is P's trade?                                  stated in K1
  R2  Who trained P?                                      stated in K2
  R3  In which town was P born?                           stated in K3
  I1  Which guild is P sworn to?                          one step of inference inside K1
  C1  In which town was the person who trained P born?    needs two seeds: K2 of P and K3 of the trainer
  C2  Which guild is the person who trained P sworn to?   needs K2 of P and K1 of the trainer, plus the rule

R = recall, I = one inference step, C = combining two seeds. In C questions the option list always
contains P's OWN town / guild, which is never the answer (the trainer's differs by construction),
so answering about P instead of the trainer is visibly wrong. Towns, crafts and guilds are balanced
(each is the answer equally often) and the correct option position cycles through A-D.
"""
import random

CRAFTS = ["glassblower", "cooper", "tanner", "weaver", "mason", "fletcher", "chandler", "wheelwright"]
GUILDS = ["Guild of the Red Heron", "Guild of the Grey Otter", "Guild of the White Stag", "Guild of the Black Wren",
          "Guild of the Green Adder", "Guild of the Golden Carp", "Guild of the Silver Moth", "Guild of the Brown Marten"]
_TOWN_A = ["Oss", "Varn", "Quill", "Drath", "Ember", "Holl", "Stry", "Wend", "Marr", "Tolg", "Ys", "Bex"]
_TOWN_B = ["enveil", "hold", "mere", "ock", "low", "garth", "wick", "ford", "rath", "stead", "umber", "ell"]
_NAME_A = ["Ta", "Mi", "Quo", "Bre", "Sel", "Dru", "Ka", "Vo", "Ysh", "Nel", "Or", "Fen", "Ha", "Lu", "Zi", "Pe",
           "Gro", "Ime", "Jas", "Wre"]
_NAME_B = ["vren", "resh", "lan", "dor", "mith", "kal", "sun", "tek", "bel", "gar", "nix", "wyn", "rok", "sal",
           "dim", "thu", "ovar", "ezzin", "ula", "orm"]
LETTERS = "ABCD"
QUESTION_TYPES = ("R1", "R2", "R3", "I1", "C1", "C2")
GROUPS = {"R": ("R1", "R2", "R3"), "I": ("I1",), "C": ("C1", "C2")}


def _names(rng, n_persons, n_towns):
    persons = []
    while len(persons) < n_persons:
        name = rng.choice(_NAME_A) + rng.choice(_NAME_B)
        if name not in persons and all(name[:4] != p[:4] for p in persons):
            persons.append(name)
    a, b = rng.sample(_TOWN_A, n_towns), rng.sample(_TOWN_B, n_towns)
    return persons, [x + y for x, y in zip(a, b)]


def build(seed=0, n_persons=32, n_learners=24):
    """Returns the world: structured facts, seeds and questions (plain dicts, JSON-serialisable)."""
    rng = random.Random(seed)
    n_cat = len(CRAFTS)
    if n_persons % n_cat or n_learners > n_persons:
        raise ValueError("persons must be a multiple of %d and learners <= persons" % n_cat)
    persons, towns = _names(rng, n_persons, n_cat)
    guild_of_craft = dict(zip(CRAFTS, rng.sample(GUILDS, n_cat)))
    crafts = CRAFTS * (n_persons // n_cat)
    rng.shuffle(crafts)
    homes = towns * (n_persons // n_cat)
    rng.shuffle(homes)
    craft = dict(zip(persons, crafts))
    town = dict(zip(persons, homes))
    guild = {p: guild_of_craft[craft[p]] for p in persons}
    # trainers: different town and different guild than the learner, no two people training each other
    learners = rng.sample(persons, n_learners)
    trainer = {}
    for p in learners:
        ok = [m for m in persons if m != p and town[m] != town[p] and guild[m] != guild[p] and trainer.get(m) != p]
        trainer[p] = rng.choice(ok)

    seeds = []
    for p in persons:
        seeds.append({"kind": "K1", "persons": [p],
                      "text": "In Veltar, every %s is sworn to the %s. %s is a %s." % (craft[p], guild[p], p, craft[p])})
        seeds.append({"kind": "K3", "persons": [p], "text": "In Veltar, %s was born in the town of %s." % (p, town[p])})
    for p in learners:
        seeds.append({"kind": "K2", "persons": [p, trainer[p]], "text": "In Veltar, %s was trained by %s." % (p, trainer[p])})
    rng.shuffle(seeds)
    for i, s in enumerate(seeds):
        s["id"] = "s%03d" % i
    sid = {(s["kind"], s["persons"][0]): s["id"] for s in seeds}

    def options(correct, pool, forced=()):
        rest = [x for x in pool if x != correct and x not in forced]
        return [correct] + list(forced) + rng.sample(rest, 3 - len(forced))

    raw = []
    for p in persons:
        raw.append(("R1", "What is %s's trade?" % p, options(craft[p], CRAFTS), [sid[("K1", p)]], p))
        raw.append(("R3", "In which town was %s born?" % p, options(town[p], towns), [sid[("K3", p)]], p))
        raw.append(("I1", "Which guild is %s sworn to?" % p, options(guild[p], GUILDS), [sid[("K1", p)]], p))
    for p in learners:
        m = trainer[p]
        raw.append(("R2", "Who trained %s?" % p, options(m, [x for x in persons if x != p]), [sid[("K2", p)]], p))
        raw.append(("C1", "In which town was the person who trained %s born?" % p,
                    options(town[m], towns, forced=[town[p]]), [sid[("K2", p)], sid[("K3", m)]], p))
        raw.append(("C2", "Which guild is the person who trained %s sworn to?" % p,
                    options(guild[m], GUILDS, forced=[guild[p]]), [sid[("K2", p)], sid[("K1", m)]], p))
    rng.shuffle(raw)
    questions = []
    count = {t: 0 for t in QUESTION_TYPES}
    for qtype, text, opts, needs, subject in raw:
        correct, others = opts[0], opts[1:]
        rng.shuffle(others)
        pos = count[qtype] % 4                     # the correct option cycles through A-D within each type
        count[qtype] += 1
        ordered = others[:pos] + [correct] + others[pos:]
        questions.append({"id": "q%03d" % len(questions), "type": qtype, "question": text, "options": ordered,
                          "answer": pos, "needs": needs, "subject": subject})
    return {"seed": seed, "persons": persons, "towns": towns, "craft": craft, "town": town, "guild": guild,
            "guild_of_craft": guild_of_craft, "trainer": trainer, "seeds": seeds, "questions": questions}


# ---------------------------------------------------------------- prompts

def question_block(q):
    return "Question: %s\n%s\nAnswer with a single letter." % (
        q["question"], "\n".join("%s. %s" % (LETTERS[i], o) for i, o in enumerate(q["options"])))


def closed_book_prompt(q):
    return "Answer the question about the land of Veltar.\n" + question_block(q)


def open_book_prompt(world, q, n_distractors=4):
    """The seeds the question needs plus a few unrelated seeds, in a fixed shuffled order."""
    rng = random.Random("%s-%s" % (world["seed"], q["id"]))
    by_id = {s["id"]: s for s in world["seeds"]}
    other = [s["id"] for s in world["seeds"] if s["id"] not in q["needs"]]
    ids = list(q["needs"]) + rng.sample(other, n_distractors)
    rng.shuffle(ids)
    facts = "\n".join("- " + by_id[i]["text"] for i in ids)
    return "Here are some facts about the land of Veltar:\n%s\n\n%s" % (facts, question_block(q))


def derive_prompt(text, n=4):
    """Round 1: what follows from ONE piece of knowledge. The prompt names no question and no answer."""
    return ("Here is a piece of knowledge:\n%s\n\nWrite %d short, different statements that follow from it. "
            "Each must be a complete sentence that can be understood on its own. One per line, no numbering." % (text, n))


def connect_prompt(a, b, n=3):
    """Round 2: what follows from TWO pieces of knowledge taken together."""
    return ("Here are two pieces of knowledge:\n1. %s\n2. %s\n\nIf they are connected, write %d short statements "
            "that follow only when both are combined. Each must be a complete sentence that can be understood on its "
            "own. One per line, no numbering. If they are not connected, write NONE." % (a, b, n))


# ---------------------------------------------------------------- checking what the model wrote

def clean_lines(text):
    out = []
    for line in text.splitlines():
        line = line.strip().lstrip("-*0123456789. )").strip()
        if line:
            out.append(line)
    return out


def _core(guild):
    return guild.replace("Guild of the ", "")


def states_guild(line, world, person):
    """The line says which guild `person` is sworn to (and is not just the rule restated)."""
    return person in line and _core(world["guild"][person]) in line and "every" not in line.lower()


def states_trainer_town(line, world, learner):
    """The line links `learner` to the town their trainer was born in."""
    m = world["trainer"][learner]
    return learner in line and world["town"][m] in line


def states_trainer_guild(line, world, learner):
    m = world["trainer"][learner]
    return learner in line and _core(world["guild"][m]) in line and "every" not in line.lower()


def consistent(line, world):
    """Crude check: every town named in the line is the birth town of someone named in it, and every
    guild named is the guild of someone named in it (lines that name nobody, e.g. a rule, pass)."""
    people = [p for p in world["persons"] if p in line]
    if not people:
        return True
    for t in world["towns"]:
        if t in line and all(world["town"][p] != t for p in people):
            return False
    for g in GUILDS:
        if _core(g) in line and all(world["guild"][p] != g for p in people):
            return False
    return True


def linked_pairs(world):
    """(K2 seed of a learner, K3 seed of the trainer): two seeds that share exactly the trainer."""
    by = {(s["kind"], s["persons"][0]): s for s in world["seeds"]}
    return [(p, by[("K2", p)], by[("K3", m)]) for p, m in world["trainer"].items()]


def unlinked_pairs(world, n, seed=0):
    """Pairs of seeds that share no person."""
    rng = random.Random("unlinked-%s-%s" % (world["seed"], seed))
    out = []
    while len(out) < n:
        a, b = rng.sample(world["seeds"], 2)
        if not set(a["persons"]) & set(b["persons"]):
            out.append((a, b))
    return out
