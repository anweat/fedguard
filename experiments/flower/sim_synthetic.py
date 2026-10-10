"""Flower simulation (ray backend) with synthetic LoRA clients: exercises GuardStrategy end to end
without training a model.

Clients add seeded noise to the received LoRA factors. With FG_ATTACK=1, partition 3 scales its update
x20 and reports num-examples x100.

  sim_synthetic.py <out_dir> <mode>     mode: plain | guard
Env: FG_ATTACK=0|1, FG_ROUNDS (default 3), FG_NODES (default 6), FG_CLIP=1 (also mount NormClip),
     FG_CLIENT_RECORD=0 (server-side capture only),
     FG_HANDSHAKE=1 (use the handshake extension layer: every node announces a number before training, the
     server adds them up and sends the total back; this changes Flower's own round protocol)
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict  # noqa: E402
from flwr.clientapp import ClientApp  # noqa: E402
from flwr.serverapp import Grid, ServerApp  # noqa: E402
from flwr.serverapp.strategy import FedAvg  # noqa: E402
from flwr.simulation import run_simulation  # noqa: E402
from safetensors.torch import save_file  # noqa: E402

MALICIOUS = 3
LAYERS, D, K, R = 2, 24, 16, 4


def initial_lora() -> dict[str, torch.Tensor]:
    g = torch.Generator().manual_seed(0)
    sd = {}
    for layer in range(LAYERS):
        for proj, d_out in (("q_proj", D), ("v_proj", 8)):
            m = f"base_model.model.model.layers.{layer}.self_attn.{proj}"
            sd[m + ".lora_A.weight"] = torch.randn(R, K, generator=g)
            sd[m + ".lora_B.weight"] = torch.randn(d_out, R, generator=g) * 0.1
    return sd


def _handshake_plugins():
    from fedguard.core.plugin import GuardPlugin
    from fedguard.core.types import Stage

    class Hello(GuardPlugin):
        """Client half of the handshake check: announce how many samples there are, then read the server's total."""
        name, at, needs = "hello", (Stage.CLIENT_ANNOUNCE, Stage.CLIENT_PRE_TRAIN), frozenset({"data", "reports"})

        def run(self, ctx):
            if ctx.stage == Stage.CLIENT_ANNOUNCE:
                return ctx.findings(attachments={"n": torch.tensor([float(len(ctx.data))])})
            total = ctx.attachment("pool.total").get("server")
            return ctx.findings(evidence={"total_from_server": None if total is None else float(total)})

    class Pool(GuardPlugin):
        """Server half: the sum of what the nodes announced goes back to all of them before they train."""
        name, at, needs = "pool", Stage.SERVER_EXCHANGE, frozenset({"reports"})

        def run(self, ctx):
            got = ctx.attachment("hello.n")
            return ctx.findings(attachments={"total": torch.stack(list(got.values())).sum(0)},
                                evidence={"announced": len(got), "total": float(sum(float(v) for v in got.values()))})
    return Hello, Pool


Hello, Pool = _handshake_plugins()


def node_data(pid: int):
    from fedguard.views.client import DataView
    return DataView([f"node {pid} sample {i}" for i in range(4)], source_of=lambda s: f"part{pid}")


def make_client_guard(context: Context):
    """Client-side capture for the guarded mode: each node keeps its own record next to the server's."""
    from fedguard.client import ClientGuard
    from fedguard.core.runner import GuardRunner
    from fedguard.core.types import RunSpec
    from fedguard.plugins import LocalCentroid
    from fedguard.recorder.store import Recorder
    node = str(context.node_id)
    plugins = [LocalCentroid()]
    if os.environ.get("FG_HANDSHAKE") == "1":
        plugins.append(Hello())
    return ClientGuard(node, GuardRunner(plugins, RunSpec("guard", lora_scale=2.0), side="client"),
                       Recorder(Path(os.environ["FG_OUT"]) / "records", "guard", scope=node))


_capture = None


def capture_mod(msg: Message, context: Context, call_next) -> Message:
    """Installed always, active only in guard mode: the mode is known when messages flow, not at import."""
    global _capture
    if os.environ.get("FG_MODE") != "guard" or os.environ.get("FG_CLIENT_RECORD", "1") != "1":
        return call_next(msg, context)
    if _capture is None:
        from fedguard.adapters.flower_client import guard_mod
        hs = os.environ.get("FG_HANDSHAKE") == "1"
        _capture = guard_mod(make_client_guard, extensions={"handshake"} if hs else (),
                             prepare=(lambda m, c, received: (node_data(int(c.node_config["partition-id"])), None)) if hs else None)
    return _capture(msg, context, call_next)


client = ClientApp(mods=[capture_mod])


@client.train()
def train(msg: Message, context: Context) -> Message:
    pid = int(context.node_config["partition-id"])
    rnd = int(msg.content["config"]["server-round"])
    base = msg.content["arrays"].to_torch_state_dict()
    g = torch.Generator().manual_seed(1000 * rnd + pid)
    if os.environ.get("FG_MODE") == "guard":
        from fedguard.adapters.flower_client import active_guard
        from fedguard.views.client import DataView
        guard = active_guard()
        if guard is not None:
            guard.pre_train(data=node_data(pid))
            guard.on_step(1, {"loss": 1.0})
    attack = os.environ.get("FG_ATTACK") == "1" and pid == MALICIOUS
    local = {k: v + (20.0 if attack else 1.0) * 0.01 * torch.randn(v.shape, generator=g) for k, v in base.items()}
    n = 100 * (100 if attack else 1)
    return Message(RecordDict({"arrays": ArrayRecord(local),
                               "metrics": MetricRecord({"num-examples": n, "train_loss": 1.0})}), reply_to=msg)


@client.query("fedguard_announce")
def announce(msg: Message, context: Context) -> Message:
    """Only reached with FG_HANDSHAKE=1: the handshake extension's query before each training round."""
    from fedguard.adapters.flower_handshake import announce_query
    handler = announce_query(make_client_guard, lambda m, c, received: (node_data(int(c.node_config["partition-id"])), None))
    return handler(msg, context)


server = ServerApp()


@server.main()
def main(grid: Grid, context: Context) -> None:
    out, mode = Path(os.environ["FG_OUT"]), os.environ["FG_MODE"]
    inner = FedAvg(fraction_train=1.0, fraction_evaluate=0.0)
    strategy = inner
    if mode == "guard":
        from fedguard.adapters.flower import GuardStrategy
        from fedguard.core.runner import GuardRunner
        from fedguard.core.types import RunSpec
        from fedguard.plugins import CentroidConsensus, EffectStats, FactorStats, ReportGuard, RobustOutlier
        from fedguard.recorder.store import Recorder
        rec = Recorder(out / "records", "guard")
        plugins = [EffectStats(), FactorStats(), RobustOutlier("effect_stats.inc_norm"), ReportGuard(), CentroidConsensus()]
        if os.environ.get("FG_CLIP") == "1":      # exercises transform_update; replay check C no longer applies
            from fedguard.plugins import NormClip
            plugins.insert(0, NormClip(ratio=2.0))
        runner = GuardRunner(plugins,
                             RunSpec("guard", lora_scale=2.0, extra={"max_num_examples": 100}), rec,
                             apply_actions=True)
        if os.environ.get("FG_HANDSHAKE") == "1":
            from fedguard.adapters.flower_handshake import HandshakeStrategy
            runner = GuardRunner([*plugins, Pool()], RunSpec("guard", lora_scale=2.0, extra={"max_num_examples": 100}), rec, apply_actions=True)
            strategy = HandshakeStrategy(inner, runner, rec)
        else:
            strategy = GuardStrategy(inner, runner, rec)
    result = strategy.start(grid=grid, initial_arrays=ArrayRecord(initial_lora()),
                            num_rounds=int(os.environ.get("FG_ROUNDS", "3")))
    save_file({k: v.contiguous() for k, v in result.arrays.to_torch_state_dict().items()},
              str(out / f"final_{mode}.safetensors"))


if __name__ == "__main__":
    os.environ["FG_OUT"], os.environ["FG_MODE"] = sys.argv[1], sys.argv[2]
    Path(sys.argv[1]).mkdir(parents=True, exist_ok=True)
    run_simulation(server_app=server, client_app=client, num_supernodes=int(os.environ.get("FG_NODES", "6")),
                   backend_config={"client_resources": {"num_cpus": 1, "num_gpus": 0.0}})
