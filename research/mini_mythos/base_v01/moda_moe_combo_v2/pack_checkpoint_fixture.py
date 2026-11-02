"""Memory-only complete small-MoE checkpoint packing fixture; no140M forward.

Builds exactly187392 adapter parameters and all16 Adam states using synthetic
finite data. Serializes to BytesIO, reloads bitwise, inspects every ZIP member.
Writes no binary/files; one JSON receipt is printed for the operator to preserve.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import sys
import zipfile

SOURCE_SHA = "335c76d353550cbd3bc409ecfae92141b1ab70265429e0f8e33ccdcb5cd06492"
WIKI_SHA = "b730b54aa1896227a67e25e6f422ea66f7c9d04ac1a17d98cfef5416d44653cc"
PROPOSED_LIMIT = 2621440
ENV = {"OMP_NUM_THREADS":"2", "MKL_NUM_THREADS":"2", "OPENBLAS_NUM_THREADS":"1",
       "CUDA_VISIBLE_DEVICES":"", "PYTHONDONTWRITEBYTECODE":"1", "HF_HUB_OFFLINE":"1",
       "TRANSFORMERS_OFFLINE":"1", "TOKENIZERS_PARALLELISM":"false", "RAYON_NUM_THREADS":"1"}

def require(ok, text):
    if not ok: raise ValueError(text)

def pin(raw): return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def load(path,name,expected):
    require(path.is_absolute() and path.is_file() and not path.is_symlink(),"Absolute regular source")
    raw=path.read_bytes();require(pin(raw)["sha256"]==expected,"Source pin: "+str(path))
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module,pin(raw)

def same(a,b,torch):
    if isinstance(a,torch.Tensor):
        require(isinstance(b,torch.Tensor) and a.shape==b.shape and a.dtype==b.dtype,"Reload tensor schema")
        require(torch.equal(a.detach().contiguous().reshape(-1).view(torch.uint8),b.detach().contiguous().reshape(-1).view(torch.uint8)),"Reload tensor bytes")
    elif isinstance(a,dict):
        require(type(a)is type(b) and set(a)==set(b),"Reload dict keys")
        for key in a: same(a[key],b[key],torch)
    elif type(a)in(list,tuple):
        require(type(a)is type(b) and len(a)==len(b),"Reload sequence schema")
        for x,y in zip(a,b):same(x,y,torch)
    else:require(type(a)is type(b) and a==b,"Reload scalar metadata")

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source",type=Path,required=True)
    cli.add_argument("--combo-model",type=Path,required=True)
    cli.add_argument("--combo-sha256",required=True)
    cli.add_argument("--development-only",action="store_true")
    args=cli.parse_args()
    report=dict(Purpose="Complete adapter/Adam/RNG archive size under actual Torch serialization",
        Environment={},Input={},Expected=dict(parameters=187392,parameter_tensors=16,optimizer_states=16,
            optimizer_step=32,maximum_archive_bytes=PROPOSED_LIMIT,real_model_loads=0,forward_calls=0,backward_calls=0,optimizer_updates=0),
        Actual={},Status="NOT TESTED")
    try:
        require(sys.flags.isolated and sys.dont_write_bytecode,"Require Python -I -B")
        require(re.fullmatch("[0-9a-f]{64}",args.combo_sha256) is not None,"Full model source SHA256")
        for k,v in ENV.items():os.environ[k]=v
        import torch
        torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        report["Environment"]=dict(python=platform.python_version(),torch=str(torch.__version__),executable=sys.executable,
            platform=platform.system(),development_only=args.development_only,threads=[torch.get_num_threads(),torch.get_num_interop_threads()],
            deterministic=torch.are_deterministic_algorithms_enabled(),memory_only=True)
        if not args.development_only:
            require(platform.system()=="Linux" and platform.python_version()=="3.12.3" and str(torch.__version__)=="2.11.0+cpu"
                    and sys.executable=="/workspaces/mythos-base-v01-cpu312/bin/python"
                    and os.environ.get("CODESPACE_NAME")=="bookish-pancake-vwqx7rr9x5w3wxjr","Actual frozen target Torch environment required")
        source,source_pin=load(args.source,"checkpoint_fixture_source",SOURCE_SHA)
        combo,combo_pin=load(args.combo_model,"checkpoint_fixture_adapter",args.combo_sha256)
        report["Input"]=dict(source_file=str(args.source),source_pin=source_pin,combo_file=str(args.combo_model),combo_pin=combo_pin,
            fixture_source_pin=pin(Path(__file__).read_bytes()) if "__file__"in globals() and Path(__file__).is_file() else None,
            actual_weights_read=False,data_files_read=False,synthetic_seed=20261103)
        torch.manual_seed(20261103)
        generator=torch.Generator(device="cpu");generator.manual_seed(20261103)
        archives=[]
        for seed in (4101,4202):
            for config in ("Esolo","HE"):
                bank=combo.MoEResidual(source,width=768,seed=seed)
                named=list(bank.named_parameters())
                require(len(named)==16 and sum(p.numel() for n,p in named)==187392,"Exact adapter parameter population")
                optimizer=torch.optim.AdamW(bank.parameters(),lr=.001,betas=(.9,.999),eps=1e-8,weight_decay=0.,foreach=False)
                with torch.no_grad():
                    for name,p in named:
                        p.copy_(torch.randn(p.shape,generator=generator,dtype=p.dtype)*.01)
                        optimizer.state[p]={"step":torch.tensor(32.,dtype=torch.float32),
                            "exp_avg":torch.randn(p.shape,generator=generator,dtype=p.dtype)*.002,
                            "exp_avg_sq":torch.rand(p.shape,generator=generator,dtype=p.dtype)*.0001+1e-10}
                state=optimizer.state_dict()
                require(len(state["state"])==16 and len(state["param_groups"])==1,"Full Adam state, including potentially unused real-run experts")
                tensors={}
                for name,p in named:
                    entry=optimizer.state[p]
                    require(set(entry)=={"step","exp_avg","exp_avg_sq"} and float(entry["step"])==32.,"Full optimizer metadata")
                    require(entry["exp_avg"].shape==entry["exp_avg_sq"].shape==p.shape,"Optimizer shape completeness")
                    require(bool(torch.isfinite(p).all()) and all(bool(torch.isfinite(v).all()) for v in entry.values()),"Finite complete synthetic state")
                    tensors[name]=dict(shape=list(p.shape),dtype=str(p.dtype),parameters=p.numel(),
                        parameter_sha256=combo.digest(p),exp_avg_sha256=combo.digest(entry["exp_avg"]),exp_avg_sq_sha256=combo.digest(entry["exp_avg_sq"]),step=32)
                checkpoint=dict(config=config,train_seed=seed,steps=32,state_dict=bank.state_dict(),optimizer=state,
                    rng_state=torch.get_rng_state(),freeze_commit="f"*40,source_sha256=SOURCE_SHA,inputs_sha256=WIKI_SHA,
                    total_parameters=187392,MoDA_updated=False)
                buffer=io.BytesIO();torch.save(checkpoint,buffer);raw=buffer.getvalue()
                restored=torch.load(io.BytesIO(raw),map_location="cpu",weights_only=True)
                same(checkpoint,restored,torch)
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    require(archive.testzip() is None,"Complete ZIP CRC check")
                    members=[dict(name=z.filename,uncompressed_bytes=z.file_size,stored_bytes=z.compress_size,compression=z.compress_type) for z in archive.infolist()]
                    require(all(z["compression"]==zipfile.ZIP_STORED for z in members),"No compression-dependent size claim")
                require(len(raw)<=PROPOSED_LIMIT,"Complete checkpoint exceeds proposed2.5MiB hard cap")
                archives.append(dict(config=config,train_seed=seed,archive=pin(raw),parameter_tensors=tensors,
                    optimizer_states=16,rng_bytes=checkpoint["rng_state"].numel(),roundtrip_bitwise=True,zip_crc_pass=True,zip_members=members))
                del bank,optimizer,state,checkpoint,restored,buffer,raw
        require(not({"parcae_lm","receval","transformers"}&{n.split(".")[0]for n in sys.modules}),"No pretrained-model library imports")
        report["Actual"]=dict(archives=archives,max_archive_bytes=max(r["archive"]["bytes"]for r in archives),
            total_archive_bytes=sum(r["archive"]["bytes"]for r in archives),proposed_per_checkpoint_cap=PROPOSED_LIMIT,
            parameters_per_adapter=187392,parameter_tensors_per_adapter=16,optimizer_states_per_adapter=16,
            small_adapter_instances=4,real_model_loads=0,forward_calls=0,backward_calls=0,optimizer_updates=0,
            binary_files_written=0,complete_roundtrip=True,all_state_fields_retained=True)
        report["Status"]="PASS"
    except BaseException as exc:
        report["Status"]="BLOCKED" if isinstance(exc,(OSError,MemoryError,KeyboardInterrupt)) else "FAIL"
        report["error"]=dict(type=type(exc).__name__,message=str(exc))
    print(json.dumps(report,sort_keys=True,allow_nan=False))
    return 0 if report["Status"]=="PASS" else 2

if __name__=="__main__":raise SystemExit(main())
