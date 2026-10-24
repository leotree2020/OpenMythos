# Git Ancestry Proof

Commands run against local clone:

```
git merge-base --is-ancestor e37cfa376b58d25e409ab761b61f8aba33f7a027 HEAD
git rev-list --count e37cfa3..HEAD
git ls-tree -r HEAD --name-only | grep GATE2_STAGE
```

Result on this branch (`mini-mythos-p1c-gate2-integrated`):
- Created from `e37cfa376b58d25e409ab761b61f8aba33f7a027`.
- `e37cfa3` is an ancestor (merge-base --is-ancestor exit 0).
- Stage A/B YAML present under `research/mini_mythos/docs/p1c/`.
- Gate 2.1 / 2.2 research trees imported from `67baeb7` without deleting the old branch.

Old branch `mini-mythos-p1c-gate2-dataloader-continuity` is unchanged.
PR #6 and #7 remain Draft. No force-push of the old branch.
