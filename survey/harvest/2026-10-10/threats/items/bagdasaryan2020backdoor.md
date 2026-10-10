## 1. 这篇论文的攻击做了什么

论文在传统 cross-device 联邦学习（图像分类的 ResNet18 与下一词预测的 2 层 LSTM，均无 LoRA/PEFT）上提出"模型投毒"：被控参与者完全控制自己的本地数据、本地训练过程（epoch 数、学习率、损失函数、批内样本构成）以及提交服务器之前的模型权重。攻击者先在本机训练出一个既保持主任务准确率、又在攻击者选定的触发子任务上输出目标标签的模型 X，然后在提交前把更新差改写为 γ(X − G^t) + G^t（γ = n/η，n 为参与者总数、η 为全局学习率），使得加权平均后新一轮全局模型被替换为 X（论文称 model replacement），单次注入即可让后门准确率在下一轮接近 100% 而不损主任务。为在异常检测下存活，论文进一步给出 constrain-and-scale（把检测目标写进损失）、train-and-scale（按检测界 S 压范数）、把缩放后的更新拆给多个合谋客户端，以及利用 Krum 选中"接近全局模型的后门模型"等变体。攻击者不控制服务器的聚合算法，也不影响良性参与者。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成两个：**触发-目标样本注入**（`trigger_target_sample_injection`）与**更新缩放**（`update_scaling`）。

- 两者目标相同（`backdoor`），但**所需能力与改动的制品不同**：前者只动客户端的数据面（`samples`），靠 `local_data + local_training`；后者动更新面（`local_update`、`uploads`），靠 `local_training + upload_content`。论文自己也把它们当作可分离的配置比较——纯数据投毒（BadNets 式）在联邦平均下被稀释、后门准确率停在 10%，而"投毒 + 缩放"单次注入即接近 100%，说明这是两种做法而不是一种。
- **不单独立第三、第四个技术**：constrain-and-scale（公式 4 的 L_class/L_ano 折中）、train-and-scale（公式 5 的 γ = S/‖X−G^t‖）、公式 6 的"拆分给 z 个合谋客户端"、以及"提交接近 G^t 的后门模型让 Krum 选中"，改变的都是缩放系数的取法与损失项，目标（后门）与改动制品（本地更新与上传）不变，因此写成 `update_scaling` 的 `stealth_measures`，不单独建条目。词预测里"只在最后一个词算损失、替换序列后缀"也只是注入技术在该任务上的实例。

## 3. 每个技术需要的能力与改动的制品

**触发-目标样本注入**：能力是 `local_data`（控制某些客户端的本地数据 → `samples`）与 `local_training`（控制本地训练过程 → `gradients`、`trace`、`local_update`）。改动的制品：`samples`（插入/替换的触发样本：触发句或带触发特征的图像）、`gradients`（批内 20/64 个后门样本贡献的梯度）、`trace`（与良性不同的 epoch 数、学习率、提前停止）、`local_update`（被污染的本地更新）。

**更新缩放**：能力是 `local_training`（训出 X）、`upload_content`（改写提交内容 → `local_update`、`uploads`）、`collusion`（把缩放后的更新拆给多个被控参与者）、`defense_knowledge`（论文按 Kerckhoffs 原则假设检测算法已知：要定 γ、α 必须知道范数界 S、余弦/聚类检测与其参数）。改动的制品只有 `local_update` 与 `uploads`——论文明确说攻击者**不能**控制服务器聚合算法，所以 `aggregate` 不在 `modifies` 里；聚合结果被替换是攻击的效果（观测面），不是它直接控制的制品。

## 4. 可能留痕的位置与依据

- **数据面（reported）**：`samples/text/sample`——论文直接构造了后门数据（触发句替换序列后缀；绿车/赛车条纹/竖条纹墙背景的汽车图）。
- **数据面（inferred）**：`samples/loss/sample`——只对最后一个词算损失、批内替换、后门损失低于 ϵ 提前停止，机制上会把触发样本的逐样本损失压到接近零；论文未在服务器侧观测它。
- **客户端训练面（reported）**：`trace/scalars/step`——论文报告攻击者用 6 个本地 epoch、初始 lr 0.05（图像）与 10 个 epoch、初始 lr 2（词预测），均与良性不同；但该坐标在客户端侧，被控客户端可伪造，只有信任 `self_client` 时才有意义。
- **上传面（reported，论文的主战场）**：`local_update/factors/module`（提交前被 γ 改写）与 `uploads/factor_delta/client`（L2 范数随 γ 增大，图 7；表 1 的范数 26.7–89.5）。这是范数类检测器唯一能看到的异常量，而论文主张安全聚合下服务器连它都拿不到。`uploads/product_delta/client`（LoRA 乘积差按同一比例放大）是把该机制映射到低秩更新后的推断。
- **聚合面（reported）**：`aggregate/result/model`——单次注入后下一轮全局模型的后门准确率立刻接近 100%（图 4a），即聚合结果几乎等于攻击者提交的 X；观测它需要触发集（防御方若同时能看到逐客户端上传，还可看到"聚合结果 ≈ 某个客户端的提交"）。
- **刻意不留痕的位置**：`uploads/probe_behavior/client`（把更新拆成 5 份使每份主任务准确率都正常，且良性客户端本身也常提交低准确率更新）与 `history/features/round`（单次注入而非每轮投毒，规避 Auror 式跨轮聚类的假设）是论文声明被规避的检测点，属于 `stealth_measures`，不写作 traces。

```json
{
  "key": "bagdasaryan2020backdoor",
  "items": [
    {
      "technique_name": "trigger_target_sample_injection",
      "summary_zh": "被控客户端把带触发特征、标注为攻击者选定目标类的样本插入或替换进本地训练批（词预测里把序列后缀换成以选定词结尾的触发句、只在最后一个词上算损失），使联合模型遇到该触发时输出目标标签。",
      "goal": ["backdoor"],
      "capabilities": ["local_data", "local_training"],
      "modifies": ["samples", "gradients", "trace", "local_update"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "论文直接构造后门数据：词预测把每条序列的后缀替换成以攻击者选定词结尾的触发句；图像任务用带后门特征的汽车图（绿色汽车、赛车条纹、竖条纹墙背景）。论文声明'只有攻击者持有后门特征图像'的数据切分不是根本要求。"
        },
        {
          "coordinate": "samples/loss/sample",
          "basis": "inferred",
          "note": "机制推断：攻击者只对序列最后一个词计算分类损失、每批用 c=20 个后门样本替换原样本，并在后门分类损失低于阈值 ϵ 时提前停止，因此触发样本上的逐样本损失会被压到接近零；论文未在服务器侧观测该量，服务器也看不到。"
        },
        {
          "coordinate": "trace/scalars/step",
          "basis": "reported",
          "note": "论文报告攻击者的本地步级超参与良性不同：CIFAR 上 6 个本地 epoch、初始 lr 0.05 且每 2 轮降为 1/10（良性为 2 epoch、lr 0.1）；词预测上 10 个 epoch、初始 lr 2（良性为 20）。该坐标在客户端侧，被控客户端自己可伪造，只有在本库信任 self_client 时才有意义。"
        },
        {
          "coordinate": "local_update/factors/module",
          "basis": "inferred",
          "note": "机制推断：被污染的本地训练会让提交前的本地因子带上后门方向；但论文的基线实验显示纯数据投毒的更新在联邦平均下被稀释并很快被遗忘（BadNets 式投毒的后门准确率停在 10%，即随机水平），所以这个位置上的差异很弱。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "词预测任务中选用更冷门的触发词与更热门的目标词，以降低提交更新的 L2 范数（表 1：is/delicious 为 53.3，tastes/delicious 为 26.7）",
        "每个批只把 c=20 个（批大小 64）样本替换为后门样本，其余保留主任务数据，使主任务准确率不下降，避免主任务准确率审计发现异常"
      ],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "update_scaling",
      "summary_zh": "被控客户端训出后门模型 X 后，在提交前把更新差放大 γ 倍（γ = n/η，或按检测界取 γ = S/‖X−G^t‖）再上传，使加权平均后新一轮全局模型被替换为 X（论文的 model replacement），并可把缩放后的更新拆给多个合谋客户端以压低每份的范数。",
      "goal": ["backdoor"],
      "capabilities": ["local_training", "upload_content", "collusion", "defense_knowledge"],
      "modifies": ["local_update", "uploads"],
      "traces": [
        {
          "coordinate": "local_update/factors/module",
          "basis": "reported",
          "note": "论文给出提交前的改写规则：提交量 = γ(X − G^t) + G^t，缩放因子 γ = n/η，实验中 n/η = 100；若不知道 n 与 η，可逐轮增大 γ 并测量后门准确率来逼近。"
        },
        {
          "coordinate": "uploads/factor_delta/client",
          "basis": "reported",
          "note": "论文测量并报告提交更新相对 G^t 的 L2 范数：范数随 γ 增大（图 7），表 1 给出不同触发/目标词对的范数 26.7–89.5。这是范数类检测器唯一能看到的异常量，而论文主张安全聚合下服务器拿不到逐客户端更新。"
        },
        {
          "coordinate": "uploads/product_delta/client",
          "basis": "inferred",
          "note": "机制推断：在 LoRA 里更新差是低秩乘积 B·A 的差，按因子整体缩放 γ 会让乘积差同比例放大；论文只在整模型权重上报告过范数，未在 LoRA 乘积差上验证。"
        },
        {
          "coordinate": "aggregate/result/model",
          "basis": "reported",
          "note": "论文报告单次注入后下一轮全局模型的后门准确率立刻接近 100%（图 4a），即聚合结果被替换为攻击者的 X。观测这一差异需要触发集（论文用 1000 个随机旋转裁剪副本）；防御方若同时能看到逐客户端上传，还可看到聚合结果几乎等于某一个客户端的提交。"
        }
      ],
      "variant_of": "model_replacement",
      "stealth_measures": [
        "把缩放后的更新拆成 z 份交给多个合谋客户端提交，使每份的范数都落在检测界 S 以内（公式 6、附录 A.1，图 11(a)、图 12）",
        "train-and-scale：按 γ = S/‖X−G^t‖₂ 先把更新范数压到检测界 S 以内（公式 5），对付只看权重幅度的欧氏距离式检测器",
        "constrain-and-scale：把检测目标写进训练损失 L_model = α·L_class + (1−α)·L_ano，L_ano 取与全局模型的 1 − cos 距离或权重可塑性惩罚，训练时就压低异常分数（公式 4、算法 2）",
        "只做单次注入而不是每轮投毒，避开 Auror 式跨轮聚类'攻击者每轮都投毒'的假设；论文还观察到在训练后段（约第 1000 轮之后）注入能在后续轮次中长期保留",
        "把 γ 取成小于 n/η 的折中：后门准确率仍然很高，但提交更新与 G^t 的距离更小、更不显眼（图 7）",
        "只在训练期注入，后门为语义触发、测试时不需要改动输入，推理侧不留修改输入的痕迹"
      ],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
