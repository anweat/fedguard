#!/usr/bin/env bash
# A control policy file on a real model, on the FedLLM-Attack host: the same short federated run (benign
# Dolly clients only) with the controls named by the older flags and with the equivalent policy file. The
# two have to mount the same controls with the same arguments, so their records must carry the same
# policy digest and their plugins must report the same thing; a third run mounts the shipped baseline.
# Env: OUT, MODEL, FG_ENV, ROUNDS (2), CLIENTS (5), STEPS (4), EXTRA
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/envs/${FG_ENV:-fl311}/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/policy_check}"; ROUNDS="${ROUNDS:-2}"; CLIENTS="${CLIENTS:-5}"; STEPS="${STEPS:-4}"
MODEL="${MODEL:?set MODEL to a local model directory}"
rm -rf "$OUT"; mkdir -p "$OUT"; : > "$OUT/status.tsv"
read -r -a EXTRA_ARGS <<< "${EXTRA:---exp_precision bf16 --exp_base_dtype bf16}"
COMMON=(--model_name_or_path "$MODEL" --use_peft --peft_lora_r 16 --peft_lora_alpha 32 --gradient_checkpointing False
  --learning_rate 1e-4 --batch_size 4 --gradient_accumulation_steps 1 --seq_length 256 --max_steps "$STEPS"
  --num_rounds "$ROUNDS" --fed_alg fedavg --template alpaca --logging_steps 1
  --num_data_per_client 300 --local_data_dir "$ROOT/external/FedLLM-Attack/gen_data"
  --benign_dataset_names _ --benign_num_clients 0 --malicious_dataset_names _ --malicious_num_clients 0
  --exp_benign dolly --exp_benign_clients "$CLIENTS" --exp_split dirichlet --exp_alpha 0.5 --exp_pool_per_client 300 --exp_pad_to 256
  --guard_client_record 1 --sample_clients "$CLIENTS" "${EXTRA_ARGS[@]}")
cat > "$OUT/equivalent.yaml" <<'YAML'
policy: 1
server:
  fail: closed
  controls:
    - {use: effect_stats, enforce: false}
    - {use: krum, args: {f: 1, m: 3}, enforce: true}
client:
  fail: closed
  controls:
    - {use: lisa_proximal, args: {rho: 0.5}, enforce: true}
YAML
run() {   # run <name> <args...>
  local name=$1 t0=$SECONDS status=ok; shift
  "$PY" "$ROOT/experiments/fedllm_attack/run_guarded.py" "${COMMON[@]}" "$@" --output_dir "$OUT/$name" --guard_record "$OUT/rec_$name" \
    > "$OUT/$name.log" 2>&1 || status=crashed
  [ "$status" != ok ] || "$PY" "$ROOT/experiments/eval/run_summary.py" "$OUT/rec_$name" > "$OUT/$name.summary" 2>&1 || status=plugin_error
  find "$OUT/$name" "$OUT/rec_$name" -name '*.safetensors' -delete 2>/dev/null || true
  printf '%s\t%s\t%s\n' "$name" "$status" "$((SECONDS - t0))" >> "$OUT/status.tsv"
  echo "-- $name: $status, $((SECONDS - t0)) s"; [ "$status" = ok ] || tail -5 "$OUT/$name.log"
}
run flags --guard_modules effect_stats,krum --guard_client_modules lisa_proximal --guard_client_apply 1 --guard_fail_policy closed \
  --guard_args '{"krum": {"f": 1, "m": 3}, "lisa_proximal": {"rho": 0.5}}'
run file --guard_policy "$OUT/equivalent.yaml"
run baseline --guard_policy "$ROOT/integrations/policies/baseline.yaml"
"$PY" - "$OUT" <<'PYEOF' || printf 'compare\tfailed\t0\n' >> "$OUT/status.tsv"
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
def record(name):
    root = next((out / f"rec_{name}").iterdir())
    run = json.loads((root / "run.json").read_text())
    rounds = [json.loads(p.read_text()) for p in sorted(root.glob("round_*/round.json"))]
    said = [(f["module"], f["stage"], f.get("scores"), [(a["action"], a["applied"]) for a in f.get("actions", [])]) for r in rounds for f in r["findings"]]
    excluded = [sorted(r["decision"]["excluded"]) for r in rounds]
    clients = sorted((root / "clients").glob("*/run.json"))          # absent when the policy mounts nothing on the clients
    return run, said, excluded, json.loads(clients[0].read_text()) if clients else {"policy": run["policy"], "plugins": []}
(fr, fs, fe, fc), (pr, ps, pe, pc) = record("flags"), record("file")
same_digest = fr["policy"]["digest"] == pr["policy"]["digest"] and fc["policy"]["digest"] == pc["policy"]["digest"]
same_mount = fr["plugins"] == pr["plugins"] and fc["plugins"] == pc["plugins"] and fr["apply_actions"] == pr["apply_actions"]
print(f"[policy] flags and file: same digest {same_digest}, same mounted controls {same_mount}, same exclusions {fe == pe}, "
      f"same findings {fs == ps} (GPU runs differ numerically, so findings are reported, not required)")
br = record("baseline")[0]
print(f"[policy] baseline: {br['policy']['name']} {br['policy']['digest'][:19]}, {len(br['plugins'])} server controls, enforced {br['apply_actions']}")
sys.exit(0 if same_digest and same_mount else 1)
PYEOF
echo "== status"; cat "$OUT/status.tsv"
! grep -qv $'\tok\t' "$OUT/status.tsv"
