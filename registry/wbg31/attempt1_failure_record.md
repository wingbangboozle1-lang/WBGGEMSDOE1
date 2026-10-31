# WBG31-E1 attempt 1: failed closed (configuration error, no pooled result)

- Process: wbg31-e1-screen-euler-channels-c2b52d92, started 2026-10-31T01:06:04Z, finished 01:09:38Z.
- Error: KeyError 'bootstrap' in scripts/run_wbg31_euler.py line 201 (pooled summary).
- Cause: the registration omitted holdout.bootstrap (WBG-C1 carries it). Fixed by amendment 2 in registry/wbg31_e1_preregistration.json (verbatim WBG-C1 values).
- Completed before the error: Euler channels built; canary leakage_suspected=false (max orientation-invariant AUC 0.6124, 23 features); per-fold continuous HOLDOUT-DTI printed:
  - NW control 0.010356 (n withheld 1920); candidate 0.010341
  - NE control 0.013056 (2385); candidate 0.012905
  - SW control 0.015192 (3780); candidate 0.014980
  - SE control 0.017521 (3245); candidate 0.017551
- Not produced: pooled summary, paired CI, dotted arm, registry gate, evidence/wbg31/e1_experiment.json.
- Control per-fold values match the WBG-C1 receipt (evidence/experiment.json) to 6 decimals, so the pipeline reproduces the anchor per fold.
- Attempt 2 is the same experiment E1; it counts once toward the 3-experiment budget.
