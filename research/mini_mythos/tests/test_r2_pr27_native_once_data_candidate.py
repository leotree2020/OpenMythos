"""R2 Gate Q: isolated PR27 native-only Worker data-loader repair tests.

Everything uses SYNTHETIC text. Real OS worker test uses a local in-memory
HF Dataset (14 Arrow shards), never the remote FineWeb Parquet source.
The candidate remains a research adapter; original PR #27 is untouched.
"""
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))

import torch
from torch.utils.data import DataLoader, IterableDataset, get_worker_info

import r2_pr27_native_once_data_candidate as q


class ToyTokenizer:
    eos_token_id=1

    def encode(self,text,add_special_tokens=False):
        if add_special_tokens:
            raise AssertionError("No special tokens when encoding")
        return [500+int(text.split(":")[1])]


class FakeHfSource:
    """Deliberately prohibit explicit .shard(): no one should call it."""
    def __init__(self, docs):
        self.docs=list(docs)
        self.shard_calls=0

    def shard(self,*args,**kwargs):
        self.shard_calls+=1
        raise AssertionError("PR27 adapter must NOT explicitly shard HF source")

    def skip(self,n):
        return FakeHfSource(self.docs[n:])

    def __iter__(self):
        yield from self.docs


class WorkerPathProbe(IterableDataset):
    """Actual process identities and synthetic first input token IDs."""
    def __init__(self, source_stream):
        super().__init__()
        self.stream=source_stream

    def __iter__(self):
        info=get_worker_info()
        if info is None:
            raise AssertionError("A real PyTorch DataLoader Worker is required")
        for x,y in self.stream:
            source_token=int(x[0].item())
            if source_token != ToyTokenizer.eos_token_id:
                yield {
                    "source_token": source_token,
                    "worker_id": info.id,
                    "worker_pid": os.getpid(),
                    "target": int(y[0].item()),
                }


class GateQTests(unittest.TestCase):
    def make_stream(self,**kw):
        return q.FineWebEduStreamNativeOnce(
            tokenizer=ToyTokenizer(),seq_len=1,**kw
        )

    def test_pinned_dataset_source_and_revisions_are_not_mutable(self):
        for overrides in (
            {"revision":"main"},
            {"dataset_name":"unknown/dataset"},
            {"dataset_config":"tiny"},
            {"split":"validation"},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError,"frozen FineWeb"):
                    self.make_stream(**overrides)

    def test_rejects_bad_lengths_and_missing_eos(self):
        for kwargs in ({"seq_len":0},{"seq_len":-1},{"seq_len":True},
                       {"skip_docs":-1},{"skip_docs":True}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    q.FineWebEduStreamNativeOnce(
                        ToyTokenizer(),**(dict(seq_len=2)|kwargs)
                    )
        class NoEos:
            eos_token_id=None
        with self.assertRaisesRegex(ValueError,"EOS"):
            q.FineWebEduStreamNativeOnce(NoEos(),2)

    def test_no_explicit_shard_and_original_x_y_packing_kept(self):
        source=FakeHfSource([
            {"text":"ID:0"},
            {"text":""},
            {"text":"ID:1"},
            {"text":"ID:2"},
        ])
        with patch.object(q,"load_dataset",return_value=source) as loader:
            rows=list(self.make_stream())
        self.assertEqual(source.shard_calls,0)
        self.assertEqual(loader.call_count,1)
        self.assertEqual(loader.call_args.kwargs,{
            "name":"sample-10BT",
            "split":"train",
            "streaming":True,
            "revision":q.FROZEN_DATASET_REVISION,
        })
        self.assertEqual(loader.call_args.args,("HuggingFaceFW/fineweb-edu",))
        self.assertTrue(all(x.dtype==torch.long and y.dtype==torch.long
                            for x,y in rows))
        # Original PR27 packs EOS across documents, one overlap token.
        self.assertEqual([
            (int(x.item()),int(y.item())) for x,y in rows
        ], [(500,1),(1,501),(501,1),(1,502),(502,1)])

    def test_skip_docs_single_worker_is_explicit_and_bounded(self):
        source=FakeHfSource([
            {"text":"ID:0"},{"text":"ID:1"},{"text":"ID:2"}
        ])
        with patch.object(q,"load_dataset",return_value=source):
            rows=list(self.make_stream(skip_docs=1))
        self.assertEqual([
            int(x.item()) for x,_ in rows if int(x.item())!=1
        ],[501,502])

    def test_skip_docs_multi_worker_fails_before_loading_data(self):
        with patch.object(q,"get_worker_info",
                          return_value=SimpleNamespace(id=1,num_workers=2)):
            with patch.object(q,"load_dataset") as loader:
                with self.assertRaisesRegex(RuntimeError,"unsupported"):
                    list(self.make_stream(skip_docs=2))
                loader.assert_not_called()
        with self.assertRaisesRegex(ValueError,"num_workers=1"):
            q.build_loader_native_once(
                ToyTokenizer(), seq_len=1,batch_size=2,
                num_workers=2,skip_docs=7
            )

    def test_malformed_document_or_bad_tokenizer_output_refused(self):
        with patch.object(q,"load_dataset",return_value=FakeHfSource(["bad"])):
            with self.assertRaisesRegex(ValueError,"mapping"):
                list(self.make_stream())
        class BadTokenizer:
            eos_token_id=1
            def encode(self,*a,**kw):
                return [1.5]
        with patch.object(q,"load_dataset",
                          return_value=FakeHfSource([{"text":"abc"}])):
            with self.assertRaisesRegex(ValueError,"integer token"):
                list(q.FineWebEduStreamNativeOnce(BadTokenizer(),1))

    def test_build_loader_parameters_and_worker_policy(self):
        with self.assertRaisesRegex(ValueError,"num_workers"):
            q.build_loader_native_once(ToyTokenizer(),1,2,num_workers=-1)
        with self.assertRaisesRegex(ValueError,"batch_size"):
            q.build_loader_native_once(ToyTokenizer(),1,0)
        loader=q.build_loader_native_once(
            ToyTokenizer(),seq_len=1,batch_size=2,num_workers=2
        )
        self.assertEqual(loader.num_workers,2)
        self.assertTrue(loader.persistent_workers)
        self.assertTrue(loader.pin_memory)
        self.assertIsInstance(loader.dataset,q.FineWebEduStreamNativeOnce)
        # Constructing a loader must not access Hub or iterate Dataset.

    @unittest.skipUnless(sys.platform=="linux", "Real OS workers need Linux")
    def test_actual_two_os_workers_cover_all_14_local_hf_shards_once(self):
        # Fork inherits the mocked load_dataset and the LOCAL ID source.
        # This is not remote Parquet and not a GPU or model training test.
        from datasets import Dataset
        texts=[f"ID:{i}" for i in range(14)]
        local=Dataset.from_dict({"text":texts}).to_iterable_dataset(
            num_shards=14
        )
        with patch.object(q,"load_dataset",return_value=local):
            loader=DataLoader(
                WorkerPathProbe(self.make_stream()),
                batch_size=None,num_workers=2,
                multiprocessing_context="fork",
                prefetch_factor=2,persistent_workers=False,
                in_order=True,timeout=45
            )
            try:
                rows=list(loader)
            finally:
                del loader
        all_ids=[int(r["source_token"])-500 for r in rows]
        self.assertEqual(len(all_ids),14)
        self.assertEqual(sorted(all_ids),list(range(14)))
        per_worker={}
        for row in rows:
            w=int(row["worker_id"])
            per_worker.setdefault(w,{"pid":int(row["worker_pid"]),"docs":[]})
            self.assertEqual(per_worker[w]["pid"],int(row["worker_pid"]))
            per_worker[w]["docs"].append(int(row["source_token"])-500)
            self.assertEqual(row["target"],1)
        self.assertEqual(set(per_worker),{0,1})
        self.assertNotEqual(per_worker[0]["pid"],per_worker[1]["pid"])
        self.assertEqual(per_worker[0]["docs"],list(range(0,14,2)))
        self.assertEqual(per_worker[1]["docs"],list(range(1,14,2)))


if __name__=="__main__":
    unittest.main()
