# Round 3 — Fork integration v0.4

**Target:** https://github.com/leotree2020/OpenMythos

This release introduces independent provenance capture and five URL parsing tests on top of v0.3. It changes no upstream model files. Provenance records local commit SHA and SHA256 of selected model/compute/source files. The repository's ownership and Fork parent cannot be authenticated by local git metadata alone.

For the first CI run, prefer CPU smoke and independent synthetic checks. Treat any failure in GQA, MLA, ACT or cache probes as a diagnostic finding requiring further investigation. The smoke suite does not train a real language model, cannot validate Mythos-equivalent performance, and doesn't establish deep recurrence extrapolation.

To study recurrence systematically after CI, pin one parent commit, inspect community PR #27, then compare at equal training compute: 1 loop, 8 loops, random loops, with independent validation held out and at least 3 seeds when resources permit. Do not change the architecture until a training baseline is reproducible.
