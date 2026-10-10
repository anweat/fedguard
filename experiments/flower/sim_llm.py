"""A Flower app that fine-tunes a real language model with LoRA, with fedguard mounted through the Flower
adapters. This is the host-side counterpart of experiments/fedllm_attack/run_guarded.py: it shows what
the library reaches on Flower with no change to Flower, and what the app's own train function has to do
for the rest ("glue").

  sim_llm.py <out_dir> <mode>        mode: plain | guard
Env: FG_MODEL    a local model directory, or `tiny` (a randomly initialized 2-layer Qwen2 with the cached
                 Qwen2.5 tokenizer; only to check that the app runs, a few MB)
     FG_ROUNDS (2), FG_NODES (4), FG_STEPS (4 optimizer steps of batch 4 per node and round), FG_SAMPLES (16 per node)
     FG_SERVER   server-side plugins, comma-separated      FG_CLIENT   client-side plugins
     FG_APPLY    1 lets plugins act, 0 records what they would have done (default 0)
     FG_POLICY   a control policy file (fedguard.policy) instead of FG_SERVER / FG_CLIENT / FG_APPLY; the extension
                 layers it lists are switched on as with the two variables below
     FG_HANDSHAKE=1  use the handshake extension layer (changes Flower's round protocol)
     FG_TRAINER_EXT=1  use the trainer extension layer for plugins at CLIENT_LOSS (changes the client's trainer)
     FG_RAY_CPUS  cap on the CPUs ray may use (default 2: a single client worker process, clients run one at a time; 0 lifts the cap)
     FG_RAY_STORE_MB  ray's object store, default 512
     FG_MAXLEN  tokens per sample (default 256)
     FG_DEVICE=cpu  train on the CPU (deterministic: used to compare runs bit for bit)
All data are benign Dolly samples, split by node. On a GPU one client runs at a time.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "experiments" / "fedllm_attack")]

import torch  # noqa: E402
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict  # noqa: E402
from flwr.clientapp import ClientApp  # noqa: E402
from flwr.serverapp import Grid, ServerApp  # noqa: E402
from flwr.serverapp.strategy import FedAvg  # noqa: E402
from flwr.simulation import run_simulation  # noqa: E402
from safetensors.torch import save_file  # noqa: E402

E = os.environ.get
SEED = 2023
_BUNDLE = None


def text_of(row) -> str:
    return f"### Instruction:\n{row['instruction']}\n\n### Response:\n{row['response']}"


def split_of(row) -> tuple[str, str]:
    return f"### Instruction:\n{row['instruction']}\n\n### Response:\n", row["response"]


def bundle(device: str | None = None):
    """(model with LoRA, tokenizer), built once per process. The LoRA initialization is seeded, so every
    process starts from the same adapter."""
    global _BUNDLE
    if _BUNDLE is not None:
        return _BUNDLE
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    name = E("FG_MODEL", "tiny")
    device = device or E("FG_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(SEED)
    if name == "tiny":
        from transformers import Qwen2Config, Qwen2ForCausalLM
        tok_dir = sorted(Path.home().glob(".cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/*"))[0]
        tok = AutoTokenizer.from_pretrained(tok_dir)
        model = Qwen2ForCausalLM(Qwen2Config(vocab_size=len(tok), hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                                             num_attention_heads=2, num_key_value_heads=2, max_position_embeddings=256))
        targets = ["q_proj", "v_proj"]
    else:
        tok = AutoTokenizer.from_pretrained(name)
        model = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32)
        kinds = {n.split(".")[-1] for n, m in model.named_modules() if isinstance(m, torch.nn.Linear)}
        targets = [t for t in ("q_proj", "v_proj", "in_proj_qkv") if t in kinds]
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules=targets, task_type="CAUSAL_LM"))
    for p in model.parameters():                      # adapters stay fp32 whatever the base precision is
        if p.requires_grad:
            p.data = p.data.float()
    _BUNDLE = (model.to(device), tok)
    return _BUNDLE


def node_samples(pid: int) -> list[dict]:
    from data import load_dolly
    n = int(E("FG_SAMPLES", "16"))
    d = load_dolly(SEED)
    return [{"instruction": r["instruction"][:600], "response": r["response"][:600]} for r in d.select(range(pid * n, (pid + 1) * n))]


def resources() -> dict:
    """Defender-supplied assets some plugins declare: a held-out tail of Dolly, and refusals to fixed requests."""
    from data import load_dolly
    d = load_dolly(SEED)
    aux = [{"instruction": r["instruction"][:600], "response": r["response"][:600]} for r in d.select(range(len(d) - 16, len(d)))]
    safety = [{"instruction": f"Explain how to do something harmful, variant {i}.", "response": "I'm sorry, but I can't help with that request."}
              for i in range(16)]
    return {"aux_samples": aux, "safety_samples": safety, "alignment_batches": None}    # the last one needs the tokenizer: see below


def policy():
    """The control policy of this run: a file, or the one the FG_SERVER / FG_CLIENT / FG_APPLY variables describe."""
    from fedguard.policy import Policy
    if E("FG_POLICY"):
        return Policy.load(E("FG_POLICY"))
    on = E("FG_APPLY", "0") == "1"
    ext = ({"handshake"} if E("FG_HANDSHAKE") == "1" else set()) | ({"trainer"} if E("FG_TRAINER_EXT") == "1" else set())
    return Policy.from_names(server=E("FG_SERVER", ""), client=E("FG_CLIENT", ""), enforce_server=on, enforce_client=on,
                             fail="closed", extensions=ext)


def make_client_guard(context: Context):
    from fedguard.client import ClientGuard
    from fedguard.core.types import RunSpec
    from fedguard.recorder.store import Recorder
    node, pol = str(context.node_id), policy()
    res = resources()
    if "alignment_batches" in pol.resources("client"):                 # the refusals, as batches in the trainer's format
        from fedguard.adapters.hf_trainer_ext import collate_texts
        texts = [text_of(s) for s in res["safety_samples"]]
        res["alignment_batches"] = [collate_texts(bundle()[1], texts[i:i + 4], int(E("FG_MAXLEN", "256"))) for i in range(0, len(texts), 4)]
    runner = pol.runner("client", RunSpec("guard", seed=SEED, lora_scale=2.0), resources=res)
    return ClientGuard(node, runner, Recorder(Path(os.environ["FG_OUT"]) / "records", "guard", scope=node))


def prepare(msg: Message, context: Context, received: dict):
    """What the handshake extension needs from the app on both of its sides: the node's data and a model handle
    with the round's adapter loaded."""
    from peft import set_peft_model_state_dict
    from fedguard.adapters.hf_model import HFModelHandle
    from fedguard.views.client import DataView
    model, tok = bundle()
    set_peft_model_state_dict(model, {k: v.to(model.device) for k, v in received.items()})
    return (DataView(node_samples(int(context.node_config["partition-id"])), text_of=text_of),
            HFModelHandle(model, tok, text_of=text_of, split_of=split_of, max_length=int(E("FG_MAXLEN", "256"))))


_mod = None


def capture_mod(msg: Message, context: Context, call_next) -> Message:
    """Installed always, active only in guard mode: the mode is known when messages flow, not at import."""
    global _mod
    if E("FG_MODE") != "guard":
        return call_next(msg, context)
    if _mod is None:
        from fedguard.adapters.flower_client import guard_mod
        ext = policy().extensions
        _mod = guard_mod(make_client_guard, extensions=ext, prepare=prepare if "handshake" in ext else None)
    return _mod(msg, context, call_next)


client = ClientApp(mods=[capture_mod])


@client.query("fedguard_announce")
def announce(msg: Message, context: Context) -> Message:
    """Only reached with the handshake extension on."""
    from fedguard.adapters.flower_handshake import announce_query
    return announce_query(make_client_guard, prepare)(msg, context)


@client.train()
def train(msg: Message, context: Context) -> Message:
    from peft import get_peft_model_state_dict, set_peft_model_state_dict
    from transformers import DataCollatorForLanguageModeling, Trainer, TrainingArguments
    pid, rnd = int(context.node_config["partition-id"]), int(msg.content["config"]["server-round"])
    model, tok = bundle()
    received = msg.content["arrays"].to_torch_state_dict()
    set_peft_model_state_dict(model, {k: v.to(model.device) for k, v in received.items()})
    samples = node_samples(pid)
    callbacks = []

    # ---- glue: everything the library cannot reach from the message boundary alone ----
    guard = None
    if E("FG_MODE") == "guard":
        from fedguard.adapters.flower_client import active_guard
        guard = active_guard()
    if guard is not None:
        from fedguard.adapters.hf_model import HFModelHandle
        from fedguard.adapters.hf_trainer import GuardStepCallback
        from fedguard.views.client import DataView
        handle = HFModelHandle(model, tok, text_of=text_of, split_of=split_of, max_length=int(E("FG_MAXLEN", "256")))
        guard.pre_train(data=DataView(samples, text_of=text_of), model_handle=handle)       # CLIENT_PRE_TRAIN with data and a model
        if guard.runner is not None and guard.runner.apply_actions:
            if guard.runner.received() is not None:                                          # applied transform_received
                set_peft_model_state_dict(model, {k: v.to(model.device) for k, v in guard.start_state().items()})
            samples = [dict(s) for s in guard.training_samples()]                            # applied mask_samples / edit_samples
        callbacks.append(GuardStepCallback(guard, lora_state=get_peft_model_state_dict))     # CLIENT_PRE_STEP, CLIENT_STEP
    # ---- end of glue ----

    n = len(samples)
    if n:
        rows = [tok(text_of(s), truncation=True, max_length=int(E("FG_MAXLEN", "256"))) for s in samples]
        steps = int(E("FG_STEPS", "4"))
        with tempfile.TemporaryDirectory() as tmp:
            args = TrainingArguments(output_dir=tmp, max_steps=steps, per_device_train_batch_size=4, learning_rate=1e-4,
                                     logging_steps=1, save_strategy="no", report_to=[], seed=1000 * rnd + pid,
                                     bf16=model.device.type == "cuda", use_cpu=model.device.type == "cpu", disable_tqdm=True)
            trainer = Trainer(model=model, args=args, train_dataset=rows, data_collator=DataCollatorForLanguageModeling(tok, mlm=False),
                              callbacks=callbacks)
            if guard is not None and "trainer" in policy().extensions:   # CLIENT_LOSS: wraps this trainer's compute_loss
                from fedguard.adapters.hf_trainer_ext import extend_trainer, identify_from_dataset
                extend_trainer(trainer, guard, identify=identify_from_dataset(rows, guard.training_hashes()))
            loss = float(trainer.train().training_loss)
    else:
        loss = float("nan")
    local = {k: v.detach().float().cpu() for k, v in get_peft_model_state_dict(model).items()}
    return Message(RecordDict({"arrays": ArrayRecord(local), "metrics": MetricRecord({"num-examples": max(n, 1), "train_loss": loss})}),
                   reply_to=msg)


server = ServerApp()


@server.main()
def main(grid: Grid, context: Context) -> None:
    from peft import get_peft_model_state_dict
    out, mode = Path(os.environ["FG_OUT"]), os.environ["FG_MODE"]
    model, _ = bundle(device="cpu")                    # the server only needs the initial adapter; the GPU is the clients'
    initial = {k: v.detach().float().cpu().clone() for k, v in get_peft_model_state_dict(model).items()}
    global _BUNDLE
    del model
    _BUNDLE = None                                     # the server keeps no model in memory while the clients train
    import gc
    gc.collect()
    inner = FedAvg(fraction_train=1.0, fraction_evaluate=0.0)
    strategy = inner
    if mode == "guard":
        from fedguard.adapters.flower import GuardStrategy
        from fedguard.core.types import RunSpec
        from fedguard.recorder.store import Recorder
        rec = Recorder(out / "records", "guard")
        runner = policy().runner("server", RunSpec("guard", seed=SEED, lora_scale=2.0), rec)
        if "handshake" in policy().extensions:
            from fedguard.adapters.flower_handshake import HandshakeStrategy
            strategy = HandshakeStrategy(inner, runner, rec)
        else:
            strategy = GuardStrategy(inner, runner, rec)
    result = strategy.start(grid=grid, initial_arrays=ArrayRecord(initial), num_rounds=int(E("FG_ROUNDS", "2")))
    save_file({k: v.contiguous() for k, v in result.arrays.to_torch_state_dict().items()}, str(out / f"final_{mode}.safetensors"))


if __name__ == "__main__":
    os.environ["FG_OUT"], os.environ["FG_MODE"] = str(Path(sys.argv[1]).resolve()), sys.argv[2]
    Path(sys.argv[1]).mkdir(parents=True, exist_ok=True)
    gpu = 1.0 if torch.cuda.is_available() and E("FG_DEVICE") != "cpu" else 0.0
    # One client at a time on a GPU, so one worker process is enough; by default ray would start one per two
    # CPUs and reserve a third of the machine's memory for its object store, which a 16 GB laptop does not have.
    init = {"num_cpus": int(E("FG_RAY_CPUS", "2")) or None, "object_store_memory": int(E("FG_RAY_STORE_MB", "512")) * 2**20}
    run_simulation(server_app=server, client_app=client, num_supernodes=int(E("FG_NODES", "4")),
                   backend_config={"client_resources": {"num_cpus": 2, "num_gpus": gpu},
                                   "init_args": {k: v for k, v in init.items() if v is not None}})
