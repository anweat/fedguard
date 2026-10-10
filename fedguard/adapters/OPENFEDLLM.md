# 接入 OpenFedLLM 系的训练脚本

OpenFedLLM、FedLLM-Attack 这类宿主是一个从头跑到尾的脚本，没有回调或插件接口。库在这里只能靠在脚本的轮次循环里加调用来挂上。
下面是全部调用点，按它们在一轮里出现的顺序。

- **最小的完整例子**：`integrations/openfedllm/main_sft_guard.py`（OpenFedLLM 原版）和 `integrations/fedllm_attack/main_sft_guard.py`（它的衍生版 FedLLM-Attack）。
  两者都由 `integrations/make_examples.py` 从宿主自己的 `main_sft.py` 生成：同一套插入，锚在两个宿主共有的行上，每处改动标 `# [guard]`，
  同目录的 `main_sft.guard.patch` 是与上游的差异。宿主脚本 125 与 131 行。有客户端插件需要模型句柄时，示例会建一个。
- **我们自己的实验驱动**：`experiments/fedllm_attack/run_guarded.py`。在同样的调用点之外，还有数据混合、计时、模型句柄等实验用的东西（标 `# [exp]`），与接入无关。

不挂任何插件、不开记录时，这些调用不改变训练结果；用 `integrations/check_bitwise.sh <宿主>` 核对：示例不挂插件、以及挂了插件但不让它动作时，最终的全局 LoRA 与宿主原脚本逐位相同。

## 一次性的准备

```python
from fedguard.adapters.openfedllm import OpenFedLLMGuard
from fedguard.adapters.hf_trainer import GuardStepCallback
from fedguard.client import ClientGuard
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec
from fedguard.views.client import DataView

spec = RunSpec(run_id=..., seed=..., num_clients=...)
guard = OpenFedLLMGuard(GuardRunner(server_plugins, spec, recorder, apply_actions=True, resources=...), recorder)
client_guards = {c: ClientGuard(f"client{c}", GuardRunner(client_plugins, spec, side="client", ...), client_recorder) for c in ...}
```

需要模型句柄的客户端插件，另建一个 `HFModelHandle(model, tokenizer, split_of=...)`；上游在第一个 Trainer 创建前把模型留在 CPU 上，
要先 `model.to(training_args.device)`，否则训练前的插件会在 CPU 上算。

两侧的运行器也可以由一份控制策略文件给出（`fedguard.policy.Policy.load(文件).runner("server" 或 "client", spec, ...)`），
生成的接入示例就是这样做的（`--guard_policy`）。

## 每一轮的调用点

| 顺序 | 脚本里的位置 | 调用 | 对应的位置 |
|---|---|---|---|
| 1 | 选出本轮客户端之后 | `guard.begin_round(round, global_dict, clients_this_round)` | `SERVER_DISTRIBUTE` |
| 2 | 任何客户端开始训练之前（仅当有握手插件） | 每个客户端 `cg.begin_round(..., defer=True)`、`cg.announce(data=..., model_handle=...)`；然后 `guard.exchange(...)`；再 `cg.deliver(...)` | `CLIENT_ANNOUNCE`、`SERVER_EXCHANGE` |
| 3 | 给客户端装载全局 LoRA 之前 | `received = guard.model_for(client)` | 下发内容可按接收方不同 |
| 4 | 建 Trainer 之前 | `cg.begin_round(round, received, data=DataView(samples, ...), model_handle=...)` 或 `cg.pre_train(...)` | `CLIENT_PRE_TRAIN` |
| 5 | 同上 | 用 `cg.start_state()` 作为训练起点，用 `cg.training_samples()` 作为训练数据 | 收到模型的改写、样本屏蔽与改写生效 |
| 6 | 建好 Trainer 之后 | `trainer.add_callback(GuardStepCallback(cg, lora_state=get_peft_model_state_dict))` | `CLIENT_PRE_STEP`、`CLIENT_STEP` |
| 6b | 同上，在加回调之前（仅当有挂在 `CLIENT_LOSS` 的插件） | `extend_trainer(trainer, cg)`（`fedguard.adapters.hf_trainer_ext`） | `CLIENT_LOSS`。**扩展层，不是宿主原版行为**：它把这个 Trainer 的 `compute_loss` 换成一层包装，启用时发出 `HostExtensionWarning` 并在记录里写上 `host_extensions: ["trainer"]` |
| 7 | 本地训练结束 | `cg.before_upload(local_lora, reported)`，然后上传 `cg.upload_state()` | `CLIENT_POST_TRAIN` |
| 8 | 同上 | `guard.on_upload(client, lora, reported, messages=cg.outbox(), attachments=cg.outbox_tensors())`；`cg.end_round()` | 上传进入服务器一侧 |
| 9 | 聚合之前 | `kept, weights = guard.before_aggregate(clients_this_round, sample_num_list)`；`guard.transformed` 里的更新替换对应客户端的 | `SERVER_RECEIVE`、`SERVER_AGGREGATE` |
| 10 | 聚合之后 | `global_dict = guard.after_aggregate(global_dict)` | `SERVER_POST_AGGREGATE` |
| 11 | 一轮结束 | `guard.end_round(meta)` | 写记录 |

训练全部结束后 `guard.finish(global_dict, num_rounds)`。

`kept` 为空（所有上传都被排除）时保留上一轮的全局模型；某个客户端的样本被全部屏蔽时，它把收到的模型原样返回。这两处是脚本自己要处理的分支。

## 这个宿主上够不着的

十一个位置都能挂。其中十个属于"改脚本"这一档；`CLIENT_LOSS`（损失已算出、尚未反向传播）宿主的 Trainer 本身不提供，
只能通过训练器扩展层到达，见上表 6b。完整的支持表：`python -m fedguard.adapters.hosts`。评估由宿主自己做，库不设评估位置。

扩展层开着、但插件只记录不动作时，训练结果与不开时逐位相同（`tests/test_trainer_ext.py`、`experiments/flower/llm_check.sh` 的 `ext_read_cpu`）。
插件一旦改了损失，这一轮的本地训练就不再是宿主自己的训练步，对比实验时要把它和"宿主原样"的运行分开报告。
