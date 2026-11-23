"""Formal, smoke and preflight modes (Implementation Task Order V1, section 7; section 2 red line 7; protocol v1.1
section 8 step 2).

A RunMode is passed to every function whose behaviour differs between the modes.
  formal     the contract's step count only (RunMode cannot be built with another); GPU only (train.train_run and
             evaluate.evaluate_model refuse any other device); Gate 0 is judged.
  smoke      a chosen, shortened step count; device checks skipped and recorded as "smoke: device check skipped";
             everything written carries SMOKE_LABEL and is refused in the formal results directory (record.py);
             Gate 0 is computed but its status is fixed to NOT_TESTED (gate.py).
  preflight  section 8 step 2 (ST11): the first configuration for exactly the protocol's preflight step count
             (train.train_run checks it against contract.preflight_steps), on the A100 with device checks; only its
             timing is used; gate.judge refuses it; its outputs carry PREFLIGHT_LABEL.
"""
from dataclasses import dataclass

FORMAL = "formal"
SMOKE = "smoke"
PREFLIGHT = "preflight"
SMOKE_LABEL = "SMOKE — NOT A RESULT"
PREFLIGHT_LABEL = "PREFLIGHT — TIMING ONLY, NOT A RESULT"
SMOKE_GATE_NOTE = "冒烟测试，不构成结论"
SMOKE_DEVICE_NOTE = "smoke: device check skipped"


@dataclass(frozen=True)
class RunMode:
    name: str
    shortened_steps: int = None     # smoke: the chosen step count; preflight: the protocol's; formal: None

    def __post_init__(self):
        if self.name == FORMAL:
            if self.shortened_steps is not None:
                raise ValueError("formal mode takes no shortened step count (got %r)" % (self.shortened_steps,))
        elif self.name in (SMOKE, PREFLIGHT):
            if type(self.shortened_steps) is not int or self.shortened_steps < 1:
                raise ValueError("%s mode needs a positive integer step count (got %r)" % (self.name, self.shortened_steps))
        else:
            raise ValueError("unknown mode %r" % (self.name,))

    @property
    def formal(self):
        return self.name == FORMAL

    @property
    def smoke(self):
        return self.name == SMOKE

    @property
    def preflight(self):
        return self.name == PREFLIGHT

    @property
    def label(self):
        return {FORMAL: None, SMOKE: SMOKE_LABEL, PREFLIGHT: PREFLIGHT_LABEL}[self.name]

    def steps(self, contract_steps):
        """Number of optimizer steps of one training run: the contract's in formal mode; otherwise the shortened
        count, which must be below the contract's."""
        if self.formal:
            return contract_steps
        if self.shortened_steps >= contract_steps:
            raise ValueError("%s steps %d must be fewer than the contract's %d" % (self.name, self.shortened_steps, contract_steps))
        return self.shortened_steps


FORMAL_MODE = RunMode(FORMAL)


def smoke_mode(steps):
    return RunMode(SMOKE, steps)


def preflight_mode(contract):
    """Protocol section 8 step 2: the preflight runs the protocol's number of steps (contract.preflight_steps)."""
    return RunMode(PREFLIGHT, contract.preflight_steps)
