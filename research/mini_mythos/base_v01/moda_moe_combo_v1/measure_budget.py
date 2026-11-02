"""Development-only stdlib serialization forecast; no real model/data imports.

Constructs every planned synthetic receipt/row/step with deterministic varying
finite numbers and high-entropy hashes, then measures actual JSON/gzip lengths.
The forecast is not a mathematical compression upper bound. Hard runtime caps
and target protection-map admission remain mandatory.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import struct
import sys

MIB = 1024**2
SEED = 20261103
CONFIGS = (("F", None),) + tuple((c, s) for s in (4101, 4202) for c in ("H", "Esolo", "HE", "EjointHoff"))
RNG = random.Random(SEED)
RAW = 8 * MIB
NONRAW = 64 * MIB
RESERVE = 256 * MIB

def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode()

def sha(raw): return hashlib.sha256(raw).hexdigest()
def random_sha(): return "%064x" % RNG.getrandbits(256)
def number(low=.001, high=6.): return RNG.uniform(low, high)
def pin_value(size=RAW): return dict(bytes=size, sha256=random_sha())

def observer(case, config):
    # Real paired h0/RNG fields are shared by all configurations of a case.
    def paired(label): return sha((str(case) + ":" + label).encode())
    with_h = config in ("H", "HE")
    return dict(h0_sha256=paired("h0"), rng_before_sha256=paired("rng0"), rng_after_sha256=paired("rng1"),
        seed=(5101, 5202)[case % 2], core_block_calls=[32, 32], adapter_calls=32,
        moda_reads=32 if with_h else 0, moda_writes=32 if with_h else 0,
        moe_calls=0 if config in ("F", "H") else 32)

def route(depth):
    indices = [RNG.sample(range(4), 2) for _ in range(128)]
    counts = [sum(i in pair for pair in indices) for i in range(4)]
    weights = [number(.03, 1.) for _ in range(4)]
    scores = [x / sum(weights) for x in weights]
    minimum, maximum = sorted((number(.02, .45), number(.46, .99)))
    return dict(depth=depth, tokens=128, counts=counts, indices_sha256=random_sha(), weights_sha256=random_sha(),
        soft_scores_sha256=random_sha(), input_sha256=random_sha(), total_assignments=256, unique_top2_ids=True,
        soft_scores_mean=scores, weights_min=minimum, weights_max=maximum,
        weight_mass_mean=number(.55, .97), weight_mass_min=number(.5, .55), weight_mass_max=number(.98, 1.),
        entropy_mean=number(.1, 1.38), top2_margin_min=number(1e-10, .05))

def parameter_shapes():
    result = {}
    for expert in ["moe.shared_experts"] + ["moe.experts." + str(i) for i in range(4)]:
        for name, shape in (("w1", [16, 768]), ("w3", [16, 768]), ("w2", [768, 16])):
            result[expert + "." + name + ".weight"] = shape
    result["moe.gate.weight"] = [4, 768]
    assert len(result) == 16 and sum(math.prod(shape) for shape in result.values()) == 187392
    return result

def state():
    return {name: dict(shape=shape, dtype="torch.float32", sha256=random_sha()) for name, shape in parameter_shapes().items()}

def grad(shape=None):
    size = math.prod(shape) if shape else 128 * 768
    return dict(present=True, finite=True, norm=number(.00001, 12.), nonzero=RNG.randint(1, size))

def receipt(targets):
    columns = {name: [] for name in ("nll", "predictions", "gold", "max", "shifted_logsumexp", "logsumexp", "top1", "top2", "top2_indices", "margin")}
    for _ in range(64):
        maximum = number(-3., 12.); gold = maximum - number(0., 12.); shifted = number(.01, 5.)
        first, second = RNG.sample(range(32768), 2); margin = number(0., 8.)
        values = dict(nll=maximum-gold+shifted, predictions=first, gold=gold, max=maximum,
            shifted_logsumexp=shifted, logsumexp=maximum+shifted, top1=maximum,
            top2=maximum-margin, top2_indices=second, margin=margin)
        for key, value in values.items(): columns[key].append(value)
    metrics = dict(nll_sum=math.fsum(columns["nll"]), nll_mean=math.fsum(columns["nll"])/64,
        correct=sum(p == t for p, t in zip(columns["predictions"], targets)), target_count=64)
    target_sha = sha(struct.pack("<64q", *targets))
    chunks = [dict(index=i, offset=i*MIB, bytes=MIB, sha256=random_sha(), sum64=number(-1e6, 1e6),
        sum_squares64=number(1e3, 1e8), min64=number(-100., -1.), max64=number(1., 100.)) for i in range(8)]
    actual = dict(raw=pin_value(), shape=[64,32768], dtype="float32-le", targets_sha256=target_sha,
        finite_components=2097152, columns=columns, chunks=chunks, metrics=metrics)
    return dict(Purpose="Independent complete MoDA+MoE scored-matrix audit",
        Environment=dict(python="3.12.3", numpy="1.26.4", executable="/workspaces/mythos-depth-data-cpu312/bin/python", development_only=False, model_imports=[]),
        Input=dict(targets_json_pin=dict(bytes=len(encoded(targets))-1, sha256=sha(encoded(targets)[:-1])), targets_sha256=target_sha),
        Expected=dict(raw_bytes=RAW, shape=[64,32768], model_imports=[]), Actual=actual, Status="PASS")

def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--checkpoint-bytes", type=int, default=4*MIB)
    cli.add_argument("--checkpoint-receipt", type=Path)
    args = cli.parse_args()
    if args.output.exists() or args.output.is_symlink(): raise RuntimeError("Preserve previous forecast; output must be new")
    if not 0 < args.checkpoint_bytes <= 4*MIB: raise ValueError("Checkpoint envelope must be positive and no greater than original4MiB")
    packing_reference = None
    if args.checkpoint_bytes != 4*MIB:
        if args.checkpoint_receipt is None or not args.checkpoint_receipt.is_file() or args.checkpoint_receipt.is_symlink():
            raise ValueError("Tighter envelope requires preserved actual target packing receipt")
        packing_raw=args.checkpoint_receipt.read_bytes();packing=json.loads(packing_raw)
        pe,pa=packing["Environment"],packing["Actual"]
        if not(packing["Status"]=="PASS" and pe["development_only"] is False and pe["platform"]=="Linux"
               and pe["python"]=="3.12.3" and pe["torch"]=="2.11.0+cpu"
               and pe["executable"]=="/workspaces/mythos-base-v01-cpu312/bin/python"
               and pa["parameters_per_adapter"]==187392 and pa["parameter_tensors_per_adapter"]==16
               and pa["optimizer_states_per_adapter"]==16 and pa["small_adapter_instances"]==4
               and pa["complete_roundtrip"] is True and pa["all_state_fields_retained"] is True
               and all(pa[key]==0 for key in ("real_model_loads","forward_calls","backward_calls","optimizer_updates","binary_files_written"))
               and pa["max_archive_bytes"]<=args.checkpoint_bytes):
            raise ValueError("Complete target packing proof does not support tighter envelope")
        if {(r["config"],r["train_seed"]) for r in pa["archives"]}!={(c,s) for c in ("Esolo","HE") for s in (4101,4202)}:
            raise ValueError("All four archive identities required")
        if any(r["archive"]["bytes"]>args.checkpoint_bytes or r["optimizer_states"]!=16 or len(r["parameter_tensors"])!=16
               or not r["roundtrip_bitwise"] or not r["zip_crc_pass"] for r in pa["archives"]):
            raise ValueError("Archive coverage/size/roundtrip mismatch")
        if packing["Input"]["source_pin"]["sha256"]!="335c76d353550cbd3bc409ecfae92141b1ab70265429e0f8e33ccdcb5cd06492" or packing["Input"]["combo_pin"]["sha256"]!=sha(Path(__file__).with_name("combo_model.py").read_bytes()):
            raise ValueError("Packing source pins differ from current exact adapter/source")
        packing_reference=dict(path=str(args.checkpoint_receipt.resolve()),bytes=len(packing_raw),sha256=sha(packing_raw),
            max_archive_bytes=pa["max_archive_bytes"],new_per_checkpoint_cap=args.checkpoint_bytes)
    measured = {}
    def add(kind, value, compressed):
        raw = encoded(value); physical = gzip.compress(raw, compresslevel=9, mtime=0) if compressed else raw
        entry = measured.setdefault(kind, dict(files=0, canonical_bytes=0, physical_bytes=0, largest_physical_file=0, compressed=compressed))
        entry["files"] += 1; entry["canonical_bytes"] += len(raw); entry["physical_bytes"] += len(physical)
        entry["largest_physical_file"] = max(entry["largest_physical_file"], len(physical))
        return dict(bytes=len(physical), sha256=sha(physical))
    data = {("wiki" if case < 32 else "news", (case if case < 32 else case-32)//2): [RNG.randrange(32768) for _ in range(64)] for case in range(0,72,2)}
    rows = []; receipt_pins = {}; final_columns = None
    for case in range(72):
        domain = "wiki" if case < 32 else "news"; index = (case if case < 32 else case-32)//2
        targets = data[domain,index]
        for slot in range(9):
            config, seed = CONFIGS[(case+slot)%9]; number_row = len(rows)
            audit = receipt(targets); actual = audit["Actual"]
            audit_name = "audits/row_%03d.json.gz" % number_row
            receipt_pins[audit_name] = add("648_individual_audit_receipts", audit, True)
            process = dict(returncode=0, timed_out=False, timeout_seconds=60, seconds=number(.1, .8),
                stdout_sha256=random_sha(), stdout_bytes=RNG.randint(13000,19000), stderr_sha256=sha(b""), stderr_bytes=0,
                targets_sha256=actual["targets_sha256"], argument_target_ids_redacted=True)
            add("657_audit_process_receipts", process, False)
            row = dict(domain=domain, config=config, train_seed=seed, eval_seed=(5101,5202)[case%2],
                article_id=sha((domain+str(index)).encode()), article_index=index, case_index=case, slot=slot,
                row_index=number_row, observer=observer(case,config), endpoint_wall_ns=RNG.randint(2_000_000_000,7_000_000_000),
                endpoint_cpu_ns=RNG.randint(3_000_000_000,10_000_000_000), **actual["metrics"],
                worker_per_token={k:actual["columns"][k] for k in ("nll","predictions")},
                logits_sha256=actual["raw"]["sha256"], targets_sha256=actual["targets_sha256"], shape=[64,32768],dtype="float32-le",
                audit_receipt=audit_name, routing=[] if config in ("F","H") else [route(i) for i in range(32)])
            rows.append(row); final_columns = actual["columns"]
    add("single_648_row_evaluation", dict(rows=rows), True)
    for seed in (4101,4202):
        for config in ("Esolo","HE"):
            for step in range(32):
                record = dict(config=config, train_seed=seed, step=step, article_id=random_sha(), targets=128,
                    loss=number(.5,12.), observer=observer(step,config), gradient_norm_before_clip=number(.1,10.),
                    parameter_gradients={name:grad(shape) for name,shape in parameter_shapes().items()},
                    per_depth_gradients=[grad() for _ in range(32)], routing=[route(i) for i in range(32)],
                    updated_state=state(), endpoint_step_seconds=number(4.,20.))
                add("128_individual_training_records", record, True)
    reload_rows = []
    for index,(config,seed) in enumerate(CONFIGS):
        audit = receipt(data["news",0]); actual=audit["Actual"]
        add("9_reload_audit_receipts", audit, True)
        add("657_audit_process_receipts", dict(returncode=0,timed_out=False,timeout_seconds=60,seconds=number(.1,.8),
            stdout_sha256=random_sha(),stdout_bytes=RNG.randint(13000,19000),stderr_sha256=sha(b""),stderr_bytes=0,
            targets_sha256=actual["targets_sha256"],argument_target_ids_redacted=True),False)
        reload_rows.append(dict(config=config,train_seed=seed,article_id=random_sha(),eval_seed=5101,
            logits_sha256=random_sha(),observer=observer(32,config),audit="audits/reload_%d.json.gz"%index,Status="PASS"))
    add("reload_and_sentinel_metadata",dict(Status="PASS",rows=reload_rows,quality_rows_added=0,new_interpreter=True),False)
    add("reload_and_sentinel_metadata",dict(identity=reload_rows[-1],raw=pin_value(),audit="audits/reload_8.json.gz"),False)
    # Model state descriptions exist before/after in main and reload. Their exact
    # field kinds are preserved; each digest is high entropy rather than allzero.
    base_state = {"native.%02d.weight"%i:dict(shape=[768,768],dtype="torch.float32",sha256=random_sha()) for i in range(63)}
    old_adapters = {arm+"_"+str(seed):state() for arm in ("shared","depth") for seed in (4101,4202)}
    for _ in range(4):
        add("base_old_adapter_before_after_descriptions",base_state,False)
        add("base_old_adapter_before_after_descriptions",old_adapters,False)
    checkpoint_rows = []
    for seed in (4101,4202):
        for config in ("Esolo","HE"):
            name=config+"_"+str(seed)
            checkpoint_rows.append(dict(config=config,train_seed=seed,path="private/"+name+".pt",pin=pin_value(args.checkpoint_bytes),
                final_state=state(),nonzero_gradient_parameter_coverage={k:True for k in parameter_shapes()}))
            add("optimizer_receipts",dict(Status="PASS",optimizer_steps=32,unused_experts_are_allowed=True,
                parameters={n:dict(expected_steps=32,actual_steps=32,exp_avg_sha256=random_sha(),exp_avg_sq_sha256=random_sha(),shape=s) for n,s in parameter_shapes().items()}),False)
    add("adapter_manifest",dict(rows=checkpoint_rows,optimizer_steps=128,source_parameters_per_run=187392),False)
    # Independent aggregate retains every per-article contrast, domain separated.
    domains={}
    for domain,count in (("wiki",16),("news",20)):
        comparisons={}
        for title in ("HE_vs_F","HE_vs_H","HE_vs_Esolo","H_vs_F","Esolo_vs_F","joint_E_inference_interaction"):
            for seed in (4101,4202):
                comparisons[title+"_"+str(seed)]=dict(delta_nll=number(-.3,.3),delta_accuracy=number(-.05,.05),
                    per_article=[dict(article_id=sha((domain+str(i)).encode()),delta_nll=number(-1.,1.),delta_correct=RNG.randint(-64,64)) for i in range(count)],
                    articles_nll_negative=RNG.randint(0,count),worst_article_delta_nll=number(.01,1.),screen="NOT ASSESSED" if title.startswith("joint") else False,
                    interpretation="DESCRIPTIVE_NONADDITIVITY" if title.startswith("joint") else "NO_QUALIFIED_IMPROVEMENT",kind="PAIRED_CONFIGURATION_DIFFERENCE")
        domains[domain]=dict(articles=count,quality_rows=count*18,comparisons=comparisons,
            means={str(c)+"_"+str(s):dict(mean_nll=number(2.,6.),correct=RNG.randint(0,count*128),scored_observations=count*128,accuracy=number(.1,.6)) for c,s in CONFIGS},
            scientific_screens={k:"FAIL" for k in ("HE_vs_F","HE_vs_H","HE_vs_Esolo")},
            timing={"models":{str(c)+"_"+str(s):dict(calls=count*2,endpoint_total_seconds=number(50.,300.),endpoint_mean_seconds=number(2.,6.),endpoint_median_seconds=number(2.,6.),endpoint_p95_seconds=number(3.,8.),process_cpu_total_seconds=number(100.,500.)) for c,s in CONFIGS},"ratios":{str(i):number(.9,2.) for i in range(6)},"screen":"NOT ASSESSED"})
    add("final_audit_full_aggregates",dict(Purpose="Independent retained-evidence MoDA+MoE final quality audit",Environment=dict(python="3.12.3",numpy="1.26.4",development_only=False),
        Input=dict(run_dir="/workspaces/mythos-evidence/base_v01/moda_moe_combo/attempt-v1",spec="/workspaces/mythos-evidence/base_v01/moda_moe_combo/attempt-v1/spec.json"),
        Expected=dict(quality_rows=648,paired_cases=72,new_model_calls=0),Actual=dict(domains=domains,total_quality_rows=648,
            independent_stream_rows=648,paired_actual_states=72,balanced_config_slots=81,receipt_pins=receipt_pins,
            input_pins={"wiki":pin_value(81885),"news":pin_value(32692)},spec_pin=pin_value(10000),evaluation_pin=pin_value(5*MIB),results_pin=pin_value(16000),model_calls=0),Status="PASS"),True)
    add("worker_aggregate_results",dict(domains={d:{"means":v["means"],"primary_comparisons":{k:{n:r[n] for n in ("delta_nll","delta_accuracy","screen")} for k,r in v["comparisons"].items() if k.startswith("HE_vs_")},"scientific_screens":v["scientific_screens"]} for d,v in domains.items()}),False)
    # Event checks are physically JSONL and completion records contain their full
    # array too. Model the duplication rather than silently counting one copy.
    events=[dict(Purpose="Finite immutable runtime / training / matrix audit check %04d"%i,
        Expected=True,Actual=True,Status="PASS") for i in range(5500)]
    event_bytes=sum(len(encoded(row)) for row in events)
    measured["event_jsonl_uncompressed"] = dict(files=2,canonical_bytes=event_bytes,physical_bytes=event_bytes,largest_physical_file=event_bytes,compressed=False)
    add("worker_completion_with_checks",dict(Purpose="CPU recipe pilot",Environment=dict(device="CPU",threads=[2,1]),
        Input=dict(freeze=random_sha()[:40],base=random_sha()[:40],mode="main"),Expected={},Actual={},Status="PASS",checks=events,
        seconds=number(1000.,6500.),error=None),False)
    external_payload=sum(v["physical_bytes"] for v in measured.values())
    margin=math.ceil(external_payload*.15)
    components=dict(measured_payload_external_and_public=2*external_payload,
        payload_variation_allowance_both_copies=2*margin,
        complete_protection_map_hard_cap_both_copies=2*4*MIB,
        four_private_E_state_Adam_RNG_checkpoint_envelopes=4*args.checkpoint_bytes,
        git_finalization_allowance=16*MIB,
        source_protocol_tests_operator_stdout_manifest_closure_allowance=MIB)
    total=sum(components.values())
    sources={}
    for name in ("run_combo.py","combo_model.py","audit_combo.py","PROTOCOL.md","PROGRAM.md",Path(__file__).name):
        path=Path(__file__).with_name(name)
        raw=path.read_bytes();sources[name]=dict(bytes=len(raw),sha256=sha(raw))
    report=dict(Purpose="New combo full-evidence development storage forecast before formal freeze",
        Environment=dict(python=platform.python_version(),executable=sys.executable,stdlib_only=True,development_only=True),
        Input=dict(synthetic_seed=SEED,source_pins=sources,quality_rows=648,training_records=128,reload_rows=9,
            new_model_calls=0,new_source_acquisitions=0,real_weights_read=False,checkpoint_packing_receipt=packing_reference),
        Expected=dict(nonraw_limit_bytes=NONRAW,raw_limit_bytes=RAW,reserve_bytes=RESERVE,
            immutable_evidence_scope_reduced=False),
        Actual=dict(measured_artifact_groups=measured,measured_payload_external_bytes=external_payload,
            payload_variation_allowance_per_copy=margin,parts=components,projected_total_nonraw_bytes=total,
            headroom_bytes=NONRAW-total,required_total_admission_bytes=NONRAW+RAW+RESERVE,
            alternative_using_measured_2MiB_map_total=total-4*MIB,
            per_checkpoint_hard_cap_bytes=args.checkpoint_bytes,
            checkpoints_have_actual_target_packing_proof=packing_reference is not None,
            no_protected_paths_or_required_payload_fields_removed=True),
        Status="PASS" if total<=NONRAW else "BLOCKED",
        limitations=["Synthetic finite varying FP64 numbers and random SHA256 strings; actual gzip sizes measured, not zero-data extrapolation.",
            "15% serialized-payload variation allowance is a planning margin, not a mathematical upper bound.",
            "Four private full E/Adam/RNG checkpoints use the recorded per-checkpoint cap; any reduction requires the exact actual-target all-state packing proof, and formal write-time caps remain mandatory.",
            "Protection maps use the4MiB per-copy hard ceiling; a2MiB alternative is descriptive only and cannot be adopted without frozen target measurement.",
            "OneMiB explicit miscellaneous allowance and16MiB Git/finalization allowance are part of the64MiB total, not extra space.",
            "Failure/interruption partial artifacts still require actual phase-cap guards and honest preservation; this success-shape forecast cannot guarantee every exception serialization fits."])
    if {"torch","numpy","parcae_lm","receval","transformers"}&set(sys.modules): raise RuntimeError("Forbidden import")
    with args.output.open("x",encoding="utf-8",newline="\n") as stream: json.dump(report,stream,sort_keys=True,indent=2,allow_nan=False);stream.write("\n")
    print(json.dumps(dict(Status=report["Status"],projected_total_nonraw_bytes=total,headroom_bytes=NONRAW-total,measured_payload_external_bytes=external_payload),sort_keys=True))
    return 0 if report["Status"]=="PASS" else 2

if __name__=="__main__":raise SystemExit(main())
