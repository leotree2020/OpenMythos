"""metrix_e1.contract: the stage B values come from the frozen files; a changed sentence stops the run
(Implementation Task Order V1, section 2 red line 6: no protocol value is written into the code)."""
import copy

import pytest

from metrix_e1 import contract as C
from metrix_e1.errors import ImplementationFail


def test_values_match_the_frozen_files(fz, contract):
    ss, dm = fz.search_space, fz.data_manifest
    tr = contract.training
    assert (tr.epochs, tr.batch_size, tr.steps_per_epoch, tr.total_steps) == (
        ss["training_contract"]["epochs"], ss["training_contract"]["batch_size_statements"],
        ss["training_contract"]["steps_per_epoch"], ss["training_contract"]["total_steps"])
    assert list(tr.training_seeds) == dm["seeds"]["TRAIN_SEEDS"]
    assert contract.statistics.bootstrap_seed == dm["seeds"]["BOOTSTRAP_SEED"]
    assert contract.arms.configs["L"] == ss["arms"]["L"]["configs"]
    assert contract.gate.g4_cb_min == 0.90 and contract.gate.g3_learned == (0.15, 0.35)
    assert contract.stops.st11_hours == 3.5 and contract.stops.st7_hours == 4.0
    assert contract.statistics.n_boot == 10000


@pytest.mark.parametrize("old,new", [
    ("| G0.4 | `Acc_CB(F)` ≥ 0.90,3 个种子都满足 |", "| G0.4 | `Acc_CB(F)` ≥ 0.90,2 个种子都满足 |"),
    ("- 次数 **10,000**;", "- 次数 **10,000** 次;"),
    ("| ST11 | 第 8 节第 2 步预检的预估总时长超过 3.5 小时 |", "| ST11 | 第 8 节第 2 步预检的预估总时长超过 3.5 个小时 |"),
])
def test_changed_protocol_sentence_stops(fz, old, new):
    f2 = copy.copy(fz)
    assert fz.protocol_text.count(old) == 1
    f2.protocol_text = fz.protocol_text.replace(old, new)
    with pytest.raises(ImplementationFail):
        C.load(f2)


def test_changed_search_space_sentence_stops(fz):
    f2 = copy.copy(fz)
    f2.search_space = copy.deepcopy(fz.search_space)
    f2.search_space["training_contract"]["warmup"] = "linear from 0 over the first 15 optimizer steps"
    with pytest.raises(ImplementationFail):
        C.load(f2)
    f2.search_space = copy.deepcopy(fz.search_space)
    f2.search_space["training_contract"]["total_steps"] = 299
    with pytest.raises(ImplementationFail):
        C.load(f2)


def test_accounting_and_status_vocabulary(fz, contract):
    from metrix_e1.errors import STATUSES
    a = contract.accounting
    assert (a.train_flops_per_param_token, a.forward_flops_per_param_token) == (6, 2)
    assert (a.dev_questions_per_fact, a.test_questions_per_fact) == (2, 3)
    assert contract.statuses == STATUSES
    assert contract.gate.t1_acc_min == 0.70


def test_changed_status_vocabulary_stops(fz):
    f2 = copy.copy(fz)
    f2.protocol_text = fz.protocol_text.replace("`BLOCKED` / `NOT_TESTED`", "`NOT_TESTED` / `BLOCKED`")
    assert f2.protocol_text != fz.protocol_text
    with pytest.raises(ImplementationFail):
        C.load(f2)
