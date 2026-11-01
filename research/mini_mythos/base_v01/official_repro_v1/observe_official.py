"""Run unchanged upstream eval.py; observe Python returns without replacing scoring."""
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import resource
import runpy
import sys
import time
import traceback


def main():
    spec_path = Path(sys.argv[1])
    spec = json.loads(spec_path.read_text())
    out = Path(spec['out_dir'])
    out.mkdir(parents=True, exist_ok=False)
    (out / 'run_config.json').write_text(json.dumps({'tokenizer_path': spec['tokenizer_path']}))
    events = (out / 'observations.jsonl').open('x', buffering=1)
    upstream = Path(spec['upstream'])
    sys.path.insert(0, str(upstream))
    import torch
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    # No manual seed, deterministic-algorithm override, autocast, or attention override.
    core_file = str(upstream / 'receval/tasks/core_eval.py')
    eval_file = str(upstream / 'scripts/eval.py')
    begin = time.monotonic()
    timings = {}
    failures = []
    counts = {'examples': 0, 'forward_model_exceptions': 0}

    def emit(kind, **values):
        events.write(json.dumps({'kind': kind, 'elapsed_s': time.monotonic()-begin,
                                 'maxrss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                 **values}, allow_nan=False) + '\n')

    def context(frame):
        f = frame
        while f is not None:
            if f.f_code.co_filename == core_file and f.f_code.co_name == 'run_core_eval':
                return {'task': f.f_locals.get('label'), 'seed': f.f_locals.get('seed')}
            f = f.f_back
        return {}

    def trace(frame, event, arg):
        if frame.f_code.co_filename != core_file or frame.f_code.co_name != 'forward_model':
            return None
        if event == 'exception':
            typ, value, _ = arg
            counts['forward_model_exceptions'] += 1
            failures.append({'type': typ.__name__, 'message': str(value), 'line': frame.f_lineno})
            emit('forward_model_exception', exception=failures[-1], **context(frame))
        return trace

    def profile(frame, event, arg):
        filename, name = frame.f_code.co_filename, frame.f_code.co_name
        if filename == eval_file and name == 'load_model' and event == 'return' and arg is not None:
            model, tokenizer = arg
            emit('loaded', model_class=type(model).__name__, mean_recurrence=model.config.mean_recurrence,
                 parameter_count=sum(p.numel() for p in model.parameters()),
                 dtypes=sorted({str(p.dtype) for p in model.parameters()}),
                 bos_id=tokenizer.bos_id, eos_id=tokenizer.eos_id, pad_id=tokenizer.pad_id,
                 tokenizer_class=type(tokenizer.processor).__name__)
            (out / 'rng_after_load.bin').write_bytes(torch.get_rng_state().numpy().tobytes())
        if filename != core_file or name not in ('evaluate_example', 'evaluate_task'):
            return
        if event == 'call':
            timings[id(frame)] = time.monotonic()
        elif event == 'return':
            loc = frame.f_locals
            values = context(frame)
            values['seconds'] = time.monotonic() - timings.pop(id(frame), time.monotonic())
            if name == 'evaluate_example':
                if type(arg) is not bool:
                    emit('example_incomplete', idx=loc.get('idx'), returned=repr(arg), **values)
                    return
                values.update(idx=loc['idx'], correct=arg)
                item = loc['data'][loc['idx']]
                values['item_sha256'] = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
                if 'input_ids' in loc:
                    values['input_shape'] = list(loc['input_ids'].shape)
                    values['starts'], values['ends'] = loc['starts'], loc['ends']
                if 'mean_losses' in loc:
                    values['mean_losses'], values['gold'] = loc['mean_losses'], item['gold']
                if 'pred_toks' in loc:
                    values['predicted_answer_tokens'] = loc['pred_toks'].tolist()
                    values['gold_answer_tokens'] = loc['actual_toks'].tolist()
                emit('example', **values)
                counts['examples'] += 1
                if failures:
                    raise RuntimeError('Observed official forward_model exception; stopping after current example')
            else:
                if not isinstance(arg, (float, int)) or not math.isfinite(arg):
                    emit('task_incomplete', returned=repr(arg), **values)
                    return
                emit('task', accuracy=arg, rows=len(loc['data']), **values)
                (out / ('rng_after_task_%s_%s.bin' % (values['seed'], values['task']))).write_bytes(
                    torch.get_rng_state().numpy().tobytes())

    emit('environment', python=sys.version, executable=sys.executable, torch=torch.__version__,
         packages={d.metadata['Name']: importlib.metadata.version(d.metadata['Name'])
                   for d in importlib.metadata.distributions()},
         threads=torch.get_num_threads(), interop=torch.get_num_interop_threads(),
         deterministic=torch.are_deterministic_algorithms_enabled(),
         default_dtype=str(torch.get_default_dtype()),
         environment={k: os.environ.get(k) for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','CUDA_VISIBLE_DEVICES','PARCAE_CACHE']})
    (out / 'rng_before_load.bin').write_bytes(torch.get_rng_state().numpy().tobytes())
    sys.argv = [eval_file, '--hf_repo', spec['model_dir'], '--out_dir', str(out),
                '--config', str(upstream / 'eval_configs/eval-core.yaml'), '--device_type', 'cpu',
                '--tasks.core.max_per_task', str(spec['max_per_task'])]
    emit('command', argv=sys.argv, spec=spec)
    code = 0
    try:
        sys.setprofile(profile)
        sys.settrace(trace)
        runpy.run_path(eval_file, run_name='__main__')
    except BaseException as exc:
        code = 2
        sys.setprofile(None)
        sys.settrace(None)
        emit('error', exception_type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc())
        traceback.print_exc()
    finally:
        sys.setprofile(None)
        sys.settrace(None)
        emit('completion', exit_code=code, counts=counts)
        events.close()
        (out / 'PROCESS_COMPLETION.json').write_text(json.dumps({'exit_code': code, 'counts': counts,
             'elapsed_s': time.monotonic()-begin, 'failures': failures}, indent=2))
    return code


if __name__ == '__main__':
    original_spec = Path(sys.argv[1]) if len(sys.argv) == 2 else None
    try:
        result = main()
    except BaseException as exc:
        sys.setprofile(None)
        sys.settrace(None)
        traceback.print_exc()
        # Separate exclusive file also covers initialization or cleanup failures.
        try:
            if original_spec is not None:
                with original_spec.with_suffix('.fatal.json').open('x') as stream:
                    json.dump({'status': 'FAIL', 'type': type(exc).__name__,
                               'message': str(exc), 'traceback': traceback.format_exc()}, stream)
        except BaseException:
            traceback.print_exc()
        result = 2
    raise SystemExit(result)
