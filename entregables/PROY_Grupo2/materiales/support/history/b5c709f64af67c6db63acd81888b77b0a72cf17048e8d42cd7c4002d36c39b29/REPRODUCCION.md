# V6 Final: portable recipe, not an executed replay

Finalization uses Python stdlib and cached JSON only. No new training, inference,
cohort generation or independent validation was executed. Human review is pending.
The frozen runner and original 21-file codepack are byte-for-byte preserved.
The pure policy enforces debt before history. Illustrative probability alone has
authorized abs_tol=1e-12, rel_tol=0; no exact numeric inference claim is made.

From this delivery root, with Docker and an EXISTING empty external output directory:

```sh
docker build -t apf3-v6-final .
docker run --rm --network none --read-only --tmpfs /tmp -v "$PWD/sources:/sources:ro" -v "/absolute/new-output:/results" apf3-v6-final replay
docker run --rm --network none --read-only --tmpfs /tmp -v "$PWD/experiment:/evidence:ro" -v "$PWD/ejemplos:/examples:ro" -v "/absolute/new-output:/results" apf3-v6-final predict3
```

Replay creates NEW /results/reproduccion/development and experiment. Predict3 creates
NEW /results/predict3. Both refuse existing targets. Never mount original evidence
writable. Keep /app and /revision paths: future predict verifies those absolute
provenance paths. /sources is read only; /results is the only output mount.
Fixed-seed replay checks reproducibility only, not a second independent validation.
These commands are a recipe, not evidence that an independent replay was performed.
Dependency resolver transitive packages are not claimed fully locked; six direct
requirements and the Python image version are pinned, not an image digest.

Read verificacion-v6-final.json before packaging. A missing TRAIN score cache is a
release blocker, not permission to infer or to modify the frozen experiment.
Document layout is verified against the existing signed-by-hash generation record;
no fresh Word, PowerPoint or PDF rendering is claimed by this stdlib verifier.
