"""
Minimal conditional resume-skip patch for OpenMythos research.

Does not modify pinned Parcae. Apply only in an isolated copy or via
a wrapper around the train-loop iterator creation.

Rule: omit the extra next() only when the dataset is RandomTokensDataset.
Do not use duck-typing on an arbitrary idx field.
"""

from recpre.huggingface_dataset import RandomTokensDataset


def create_train_iterator(train_dataloader, microbatch_step: int):
    """
    Drop-in replacement for the resume iterator setup in scripts/train.py.

    Native code:
        train_iterator = iter(state["train_dataloader"])
        if state["microbatch_step"] > 0:
            next(train_iterator, None)

    This version skips the extra next() only for RandomTokensDataset.
    Other datasets keep the original skip until they are verified.
    """
    train_iterator = iter(train_dataloader)
    if microbatch_step > 0:
        ds = getattr(train_dataloader, "dataset", None)
        if not isinstance(ds, RandomTokensDataset):
            next(train_iterator, None)
    return train_iterator
