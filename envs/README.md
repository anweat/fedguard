# 环境

## fl311：统一环境（P0a 结论：可用）

一套环境同时运行 FedLLM-Attack 实验和 Flower 产品原型。

```bash
uv venv --python 3.11 envs/fl311/.venv
uv pip install --python envs/fl311/.venv/bin/python -r envs/fl311/requirements.txt
```

实测版本（2026-09-30，Mac arm64）：Python 3.11.16、torch 2.10.0、transformers 4.53.0、trl 0.8.1、peft 0.6.2、datasets 4.8.5、accelerate 1.15.0、flwr 1.39.0，MPS 可用。

### P0a 冒烟测试

`experiments/fedllm_attack/launch_upstream.py` 原样运行上游 `main_sft.py`；运行时处理集中在 `_shims.py`，受保护的主循环 `run_guarded.py` 共用同一份（external/ 下文件未修改）：
Qwen2.5-0.5B-Instruct、LoRA r=8、1 个良性 + 1 个"恶意"客户端（Level3 本地数据）、2 轮 × 2 步，MPS 上 24 秒跑完，loss 正常，checkpoint 和 `training_loss.npy` 正常落盘。

| 问题 | 原因 | 处理 |
|---|---|---|
| `LoraConfig` 未指定 `target_modules`，peft 0.6.2 没有 qwen2 的默认映射 | peft 版本早于 Qwen2 | 启动器里注册 `qwen2 → [q_proj, v_proj]`；我们自己的适配器直接显式传 `target_modules` |
| 不量化时反向报错 "does not require grad" | 梯度检查点 + PEFT 需要 `enable_input_require_grads()`；8-bit 加载时由 `prepare_model_for_kbit_training` 自动处理 | Mac 上传 `--gradient_checkpointing False`；适配器里对非量化模型调用 `enable_input_require_grads()` |
| **上游不可复现**：定义了 `--seed`（默认 2023），但在 `get_peft_model` 之前从未设置 torch 随机种子，每次运行的 LoRA A 初始化都不同 | 上游缺陷；HF Trainer 的 `set_seed` 在模型创建之后才执行 | `_shims.py` 在创建模型前用 `--seed` 设置 random / numpy / torch 的种子。**多种子实验必须经过这层处理，否则"种子"只影响数据顺序，不影响初始化** |
| 响应模板 `encode(...)[2:]` 是为 Llama 写的 | Qwen 分词器下完整模板 `\n### Response:` 因上下文切分不同而匹配不到 | 已验证：切片后 ` Response:` 恰好能匹配，监督 token 数 = 回复长度 + 1（EOS），**掩码正确**。换模型时必须重新验证 |

### 未验证 / 待定

- **8-bit / 4-bit 量化**：Mac 上没有 bitsandbytes，服务器上加装 `bitsandbytes==0.49.1` 后需再跑一次冒烟测试。
- **flwr 1.40**：尚未发布到 PyPI，当前用 1.39.0；`flwr.serverapp.strategy`（FedAvg、Krum、Bulyan 等）和 `flwr.clientapp.mod` 均已具备。
- **对话模板**（P2 决策）：FedLLM-Attack 用 alpaca 模板包装，而 Qwen2.5-Instruct 的安全对齐是在其原生 chat 模板上训练的。用 alpaca 模板时，基座的拒答率会偏低，C0 的安全基线要在两种模板下各测一次再定。
- FedProx / SCAFFOLD 的 `compute_loss` 覆盖写法与 transformers 4.53 的签名（新增 `num_items_in_batch`）不兼容；基准实验只用 FedAvg，暂不处理。

### 本机运行注意

- **MPS 显存增长导致 OOM（已定位）。** 上游的整理器把每个 batch 补齐到本 batch 最长样本，形状每次不同，MPS 分配器的缓存堆只增不减：实测每训练一个客户端，驱动占用增加约 0.9 GB，而活跃张量稳定在约 1.9 GB，`torch.mps.empty_cache()` 也回收不了。10 个客户端约 4 轮后 OOM。处理：`run_guarded.py --exp_pad_to 256` 把每个 batch 补齐到固定长度（loss 有掩码，数学上等价），8 次客户端训练后驱动占用只从 3.9 GB 增到 4.25 GB，速度不变。仍有每个客户端约 40 MB 的对象残留，200 次训练约 8 GB，暂不处理。`--exp_free_cache 1`（默认开）在每个客户端后做 gc 和 `empty_cache`。这两项只在实验入口里，不影响与上游的逐位对照。
- 本机 24 GB 统一内存，训练时不要再并行跑 ray 仿真等重任务。
- MPS 上一轮 10 个客户端 × 5 步（batch 4、序列 256）约 100 秒；需要逐位可复现的对照实验用 `--device cpu`。

### Flower 仿真

- `flwr[simulation]==1.39.0` 带 ray 2.55.1。`experiments/flower/flower_check.sh` 用合成 LoRA 客户端验证 `GuardStrategy`，每次运行约 1 分钟。
- Flower 按回复到达顺序聚合，**原生 FedAvg 在两次运行之间不能逐位复现**（float32 累加顺序不同，相对差约 3e-7）。`GuardStrategy` 会先按节点 id 排序，但仿真引擎每次运行都重新分配随机节点 id，所以只保证"单次运行可以由记录逐位重算"。

## legion：RTX 4050 Laptop（6 GB），WSL2 Ubuntu 26.04

小型实验都放在这里跑（2026-09-30 起）。从 Mac 用 `ssh legion` 登录（走 Tailscale），在 WSL 里执行：`ssh legion "wsl -d Ubuntu -- bash -s" < 脚本`。
Windows 默认的命令行是 cmd，命令里的 `|`、`>` 会被 cmd 自己解释，所以要通过标准输入传脚本，传文件用 `wsl -- dd of=...`。
WSL 在最后一个会话退出时会清掉后台进程（`nohup` 没用），长任务要在 Mac 端保持一个 SSH 会话。

- **网络**：GitHub 很慢，HuggingFace 连不上；Windows 上的 localhost 代理在 WSL NAT 模式下用不了。
  安装用 `envs/setup_linux_cuda.sh`，配合镜像：`UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple`、
  `UV_PYTHON_INSTALL_MIRROR=https://registry.npmmirror.com/-/binary/python-build-standalone`；
  模型和数据集用 `HF_ENDPOINT=https://hf-mirror.com` 下载，运行时设 `HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1`。
- **实测**：torch 2.10.0+cu128，bitsandbytes 0.49.1，单元测试全部通过。

### 精度与速度（Qwen2.5-0.5B，LoRA r=16，5 步 × batch 4 × 序列 256，每个客户端）

| 设置 | 秒/客户端 | 前三个客户端的 loss | 说明 |
|---|---|---|---|
| fp32（上游默认） | 6.6 | 2.722 / 2.967 / 2.304 | 与 Mac M 系列 MPS 基本相同，张量核心没用上 |
| `--exp_precision tf32` | 4.0 | 2.722 / 2.967 / 2.304 | 与 fp32 在 3 位小数内相同 |
| `--exp_precision bf16` | **2.0** | 2.726 / 2.971 / 2.307 | **legion 默认用这个** |
| `--load_in_4bit` | 2.95 | 2.917 / 3.137 / 2.479 | 量化误差使 loss 偏高 |
| `--load_in_8bit` | 失败 | — | `'MatmulLtState' object has no attribute 'memory_efficient_backward'`：peft 0.6.2 的 8-bit LoRA 层引用了 bitsandbytes 新版已删除的属性 |

**8-bit 路径在这组依赖下不可用。** 服务器（48/80 GB）上 7B 直接用 bf16（权重约 15 GB），需要省显存时用 4-bit（FlowerTune 的默认）。不再依赖 FedLLM-Attack 默认的 8-bit。
