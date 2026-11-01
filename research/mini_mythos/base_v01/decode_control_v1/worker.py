"""Fresh interpreter worker. Numerical libraries imported only after runtime setup."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import signal
import traceback
from run_decode_control import (SPACE, REPO, REL, BASE_REL, VENV, MODEL_DIR, TOKENIZER,
                               UPSTREAM, INFERENCE_RUN, RUNTIME_ENV, save, utc, digest, Stop)

def module_from_file(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module);return module

def runtime_state(torch):
    return {"intra_op":torch.get_num_threads(),"inter_op":torch.get_num_interop_threads(),
            "deterministic":torch.are_deterministic_algorithms_enabled(),
            "dtype":str(torch.get_default_dtype()),"device":str(torch.get_default_device()),
            "autocast_cpu":torch.is_autocast_enabled("cpu"),"autocast_cuda":torch.is_autocast_enabled("cuda"),
            "cuda_initialized":torch.cuda.is_initialized(),"dont_write_bytecode":sys.dont_write_bytecode,
            "env":{k:os.environ.get(k) for k in RUNTIME_ENV}}

def runtime_ok(s):
    return (s["intra_op"]==s["inter_op"]==1 and s["deterministic"] and s["dtype"]=="torch.float32"
            and s["device"]=="cpu" and not s["autocast_cpu"] and not s["autocast_cuda"]
            and not s["cuda_initialized"] and s["dont_write_bytecode"] and s["env"]==RUNTIME_ENV)

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);p.add_argument("--reference");p.add_argument("--implementation-commit",required=True)
    args=p.parse_args();root=Path(args.output)
    root.mkdir();public=root/"public";private=root/"private";public.mkdir();private.mkdir()
    checks=[];gates={f"D{i}":"NOT TESTED" for i in (1,2,3)}
    started=utc();status="NOT TESTED";phase="D1";inference_result=None;stop=None;loader_attempts=0
    def interrupted(signum, frame):raise Stop("BLOCKED","Worker interrupted",signum)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    def require(condition, failure, purpose, actual, expected=True):
        row={"utc":utc(),"phase":phase,"Purpose":purpose,"Environment":{"codespace":SPACE,"pid":os.getpid(),"implementation_commit":args.implementation_commit},
             "Input":"Frozen local model and tokenizer","Expected":expected,"Actual":actual,"Status":"PASS" if condition else failure}
        checks.append(row);save(public/f"worker_check_{len(checks):03d}.json",row)
        if not condition:raise Stop(failure,purpose,actual)
    try:
        require("torch" not in sys.modules and "parcae_lm" not in sys.modules,"BLOCKED","Fresh numeric interpreter",list(x for x in ("torch","parcae_lm") if x in sys.modules))
        require(sys.executable==str(VENV/"bin/python") and sys.prefix==str(VENV) and os.environ.get("CODESPACE_NAME")==SPACE,
                "BLOCKED","Frozen worker interpreter and machine",{"executable":sys.executable,"prefix":sys.prefix,"codespace":os.environ.get("CODESPACE_NAME")})
        before_env={k:os.environ.get(k) for k in RUNTIME_ENV}
        os.environ.update(RUNTIME_ENV);sys.dont_write_bytecode=True
        sys.pycache_prefix=str(private/"pycache");os.environ["PYTHONPYCACHEPREFIX"]=sys.pycache_prefix
        import torch
        require(torch.__version__=="2.11.0+cpu" and torch.version.cuda is None and Path(torch.__file__).resolve().is_relative_to(VENV),
                "BLOCKED","Frozen CPU Torch",{"version":torch.__version__,"cuda":torch.version.cuda,"file":torch.__file__})
        torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        torch.set_default_dtype(torch.float32);torch.set_default_device("cpu");torch.manual_seed(0)
        before=runtime_state(torch);require(runtime_ok(before),"BLOCKED","Actual runtime before upstream import",before)
        sys.path.insert(0,str(UPSTREAM));import parcae_lm
        official=module_from_file("mythos_frozen_receval_parcae",UPSTREAM/"receval/models/parcae.py")
        after=runtime_state(torch)
        require(before==after and runtime_ok(after),"BLOCKED","No runtime mutation by upstream import",after,before)
        require(Path(parcae_lm.__file__).resolve()==UPSTREAM/"parcae_lm/__init__.py" and
                Path(official.ModelingParcae.from_pretrained.__func__.__code__.co_filename).resolve()==UPSTREAM/"receval/models/parcae.py",
                "BLOCKED","Pinned official module origins",{"parcae":parcae_lm.__file__,"loader":official.__file__})
        save(public/"runtime.json",{"pid":os.getpid(),"ppid":os.getppid(),"process_started":started,"python":sys.version,
             "env_before":before_env,"before_upstream":before,"after_upstream":after,"torch_build":torch.__config__.show(),
             "cpu_capability":torch.backends.cpu.get_cpu_capability(),"lscpu":subprocess.run(["lscpu"],capture_output=True,text=True).stdout,
             "inference_backend":"torch.nn.attention.sdpa_kernel(SDPBackend.MATH)","state_init":"original like-init; seed once per complete call"})
        checker=module_from_file("mythos_frozen_state_checks",REPO/BASE_REL/"load_integrity_v1/state_checks.py")
        source=torch.load(MODEL_DIR/"pytorch_model.bin",map_location="cpu",weights_only=True)
        normalized,provenance=checker.normalize_checkpoint(source)
        save(public/"normalization.json",provenance)
        loader_attempts+=1
        model=official.ModelingParcae.from_pretrained(MODEL_DIR,device="cpu",dtype=None)
        require(type(model) is official.ModelingParcae and all(not m.training for m in model.modules()),"FAIL","Exact official evaluation model",{"type":type(model).__name__,"training":model.training})
        require(not model.gradient_checkpointing and not model.monitoring,"BLOCKED","No checkpointing or monitoring side path",{"gradient_checkpointing":model.gradient_checkpointing,"monitoring":model.monitoring})
        config={k:getattr(model.config,k) for k in ("state_init","attn_impl","mean_recurrence","block_size","padded_vocab_size","recurrent_iteration_method","sampling_scheme")}
        require(config=={"state_init":"like-init","attn_impl":"flash","mean_recurrence":8,"block_size":2048,"padded_vocab_size":32768,"recurrent_iteration_method":"per-sequence","sampling_scheme":"poisson-truncated-full"},"BLOCKED","Frozen model configuration",config)
        def compare_state(label):
            rows=[]
            with torch.no_grad():report=checker.compare_state(torch,normalized,model,rows.append)
            save(public/f"state_{label}.json",{"report":report,"rows":rows})
            require(report["status"]=="PASS" and len(rows)==63 and all(r["bytewise_equal"] and r["hash_complete"] and r["bytes_hashed"]==r["expected_bytes"] for r in rows),
                    report["status"] if report["status"] in ("FAIL","BLOCKED") else "FAIL","All 63 restored state entries byte-identical: "+label,
                    {"status":report["status"],"rows":len(rows),"errors":report["errors"]})
            left,right=model.transformer.wte.weight,model.lm_head.weight
            alias={"same_object":left is right,"same_storage":left.untyped_storage().data_ptr()==right.untyped_storage().data_ptr(),
                   "same_offset":left.storage_offset()==right.storage_offset(),"same_shape":left.shape==right.shape,"same_stride":left.stride()==right.stride()}
            require(all(alias.values()),"FAIL","Tied embedding/head alias preserved: "+label,alias)
            return rows
        compare_state("before")
        from tokenizers import Tokenizer
        token_module=module_from_file("mythos_frozen_tokenizer_checks",REPO/BASE_REL/"cpu_inference_v1/tokenizer_checks.py")
        validate_tokenizer=token_module.validate_tokenizer
        tokenizer=Tokenizer.from_file(str(TOKENIZER))
        token_report=validate_tokenizer(tokenizer,json.loads(TOKENIZER.read_text()),json.loads((REPO/BASE_REL/"tokenizer_probes_v1.json").read_text()),json.loads((REPO/BASE_REL/"prompts_v1.json").read_text()))
        save(public/"tokenizer.json",token_report)
        require(token_report["status"]=="PASS","FAIL","Tokenizer and fixed prompt acceptance",token_report["status"])
        gates["D1"]="PASS";phase="D2"
        from generation_checks import run_generation
        with torch.no_grad():
            inference_result=run_generation(torch,model,tokenizer,token_report["prompts"],root/"generation",INFERENCE_RUN/"first/inference")
        require(inference_result["status"]=="PASS","FAIL","Generation control terminal evidence",inference_result["status"])
        gates["D2"]="PASS";gates["D3"]="PASS"
        phase="D3"
        compare_state("after")
        require(runtime_ok(runtime_state(torch)),"BLOCKED","Runtime remains CPU and deterministic after inference",runtime_state(torch))
        require(all(p.grad is None for p in model.parameters()),"FAIL","No gradients created",{"all_grad_none":all(p.grad is None for p in model.parameters())})
        status="PASS"
    except BaseException as exc:
        status=getattr(exc,"status","BLOCKED")
        if status not in ("FAIL","BLOCKED"):status="BLOCKED"
        phase=getattr(exc,"phase",phase)
        if phase=="D3" and gates["D1"]=="PASS":gates["D2"]="PASS"
        gates[phase]=status
        stop={"phase":phase,"reason":getattr(exc,"reason",str(exc)),"actual":getattr(exc,"actual",None),"type":type(exc).__name__}
        try:save(public/"exception.json",{"stop":stop,"traceback":traceback.format_exc()})
        except BaseException as save_exc:
            stop["evidence_save_error"]=repr(save_exc)
    summary={"status":status,"gates":gates,"pid":os.getpid(),"ppid":os.getppid(),"process_started":started,"finished":utc(),
             "reference":args.reference,"official_loader_calls":loader_attempts,"official_loader_returned":1 if "model" in locals() else 0,
             "inference":inference_result,"stop":stop,"implementation_commit":args.implementation_commit}
    save(public/"summary.json",summary)
    print(json.dumps(summary,ensure_ascii=False,allow_nan=False),flush=True)
    return 0 if status=="PASS" else 2

if __name__=="__main__":sys.exit(main())
