"""Stop and failure signals of METRIX E1-PILOT.

Protocol v1.1 section 9 (fixed status vocabulary) and section 11 (stop conditions). A ProtocolStop carries the stop
condition (e.g. "ST12") when one applies and the section 9 status the run must be given. Stage B (stops.py) adds the
remaining stop conditions; this module only holds the classes the data side needs.
"""

# Checked against the frozen protocol's section 9 line by contract.check_status_vocabulary (contract.load).
STATUSES = ("PASS", "HYPOTHESIS_FAIL", "IMPLEMENTATION_FAIL", "OPTIMIZATION_FAIL", "CAPACITY_LIMIT",
            "OPTIMIZATION_OR_CAPACITY_UNRESOLVED", "BLOCKED", "NOT_TESTED", "PIPELINE_NOT_QUALIFIED")


class ProtocolStop(Exception):
    """A condition of the protocol that stops the run. `stop` is the section 11 code or None; `status` is a section 9
    status, or None only for ST6 where no status is decided yet (train.NonFinite) or none applies (stops.st6 outside
    the selected configurations and the controls: the run's configuration is excluded from selection)."""

    def __init__(self, stop, status, message):
        if status not in STATUSES and not (status is None and stop == "ST6"):
            raise ValueError("status %r is not in the protocol section 9 vocabulary" % (status,))
        self.stop = stop
        self.status = status
        super().__init__("%s%s: %s" % (stop + " -> " if stop else "", status or "no pilot status", message))


class ST12Error(ProtocolStop):
    """Protocol section 11, ST12: a hash of data, manifest, template or candidates, or the model or tokenizer version,
    differs from the frozen value -> stop; BLOCKED."""

    def __init__(self, message):
        super().__init__("ST12", "BLOCKED", message)


class ST8Error(ProtocolStop):
    """Protocol section 11, ST8: the environment does not satisfy section 0 (e.g. library versions differ from
    DATA_MANIFEST.json model.libraries) -> BLOCKED."""

    def __init__(self, message):
        super().__init__("ST8", "BLOCKED", message)


class ImplementationFail(ProtocolStop):
    """Protocol section 9, IMPLEMENTATION_FAIL raised by data generation: a name stream exhausted (2.2), a distractor
    pool with too few answers (2.5), the Y / F token ratio outside its interval (2.6)."""

    def __init__(self, message):
        super().__init__(None, "IMPLEMENTATION_FAIL", message)
