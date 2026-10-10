# gao2019strip：STRIP（STRong Intentional Perturbation，强意图扰动）运行时木马输入检测

## 1. 方法一句话

输入是一张已部署模型即将推理的待检图像 x、用户自己留存的干净参考图集 D_test、以及已部署的 DNN 模型 F_Θ()；方法对 x 做 N 次线性混合（linear blend，等权叠加另取一张参考图），把 N 张扰动图连同 x 一起送进模型，统计 N 个预测 softmax 分布的 Shannon 熵均值 H；输出是一个布尔判定 trojanedFlag（Yes/No），并据此判定该输入是否带木马触发器、进而推测所部署模型很可能被植入后门（第 IV-A 节、Algorithm 1）。方法本身不修改模型或数据，是纯检测。

## 2. 运行位置

按论文原始设定，STRIP 是"分析：集中式部署场景"下的运行时（run-time）检测模块，位于**已部署模型完成一次前向推理的同一位置**：输入 x 进入模型之前先做扰动，扰动后的 N 张图与 x 并发送入模型，随后由预测类别分布算出熵并判定（第 IV-A 节："The run-time STRIP trojan detection system is depicted in Fig. 6 and summarized in Algorithm 1"；"All the perturbed inputs along with x itself are concurrently fed into the deployed DNN model"）。它不需要客户端与服务器之间的额外往返（needs_round_trip 为 false），也不需要重新训练或访问模型内部。

对应到联邦流程：最自然的位置是**客户端收到待预测样本、把样本送进本地模型之前**（即"客户端训练前"这一时隙，用于数据准入/异常样本过滤），因为论文强调该方法只看输入与模型输出、黑盒、即插即用（plug and play）。需要明确：论文并没有在联邦学习流程里实现或评测 STRIP，"客户端训练前"是分析得到的映射；论文只在相关工作里提到联邦学习可被 1% 以内参与者植入后门（第 VII-A 节引 Bagdasaryan 等 [10]）。

## 3. 算子流水线

以下所有下标约定：n = 1…N 为扰动副本序号，i = 1…M 为类别序号，M 为类别总数；输入图像按论文实验的分辨率取值（MNIST 28×28×1，CIFAR10 与 GTSRB 32×32×3，表 I）。

### 步骤 1：参考图采样（sample_reference_batch）
- 输入：用户留存的干净测试/验证数据集 D_test（论文实验中 MNIST、CIFAR10、GTSRB 均为此目的留出样本，第 V-B 节）。
- 计算：对第 n 个副本，从 D_test 中**随机抽取**一张图像 x_n^t；Algorithm 1 第 4 行写作"randomly drawing the nth image, x_n^t, from D_test"。N 张参考图构成采样集合。
- 输出：N 张参考图 {x_1^t, …, x_N^t}，形状同输入图像。
- 论文出处：Algorithm 1 第 3–6 行；第 IV-A 节；第 III 节（"other digit images with correct ground-truth labels are randomly drawn"）。

### 步骤 2：线性混合生成扰动图（linear_blend）
- 输入：待检输入 x 的 N 份副本，以及步骤 1 的 N 张参考图 x_n^t。
- 计算：逐像素、逐通道加权叠加，x_n^p = α·x + β·x_n^t。论文只说明是"image linear blend—superimposing two images"，并在第 III 节脚注 2 指出实现用 `cv2.addWeighted()`；图 3、图 4 的例子（顶层数字 5、3、0、7 与底层数字 8 混合）显示 α = β = 0.5 的等权混合，但**论文未以公式或文字明确给出 α、β 的取值**。
- 输出：N 张扰动图 D_p = {x_1^p, …, x_N^p}（第 IV-A 节称之为 perturbation set）。
- 论文出处：第 IV-A 节；Algorithm 1 第 5 行；第 III 节及脚注 2。

### 步骤 3：逐副本前向推理取 softmax（model_forward_softmax）
- 输入：N 张扰动图 D_p，以及原图 x 本身。
- 计算：把 D_p 中的每张图送入已部署模型 F_Θ() 得到类别概率向量 y^(n) ∈ R^M（softmax 输出）；同时用 x 得到原图预测标签 z = argmax_i y_i（第 II-A 节）。
- 输出：N×M 的概率矩阵，以及原图标签 z。
- 论文出处：第 IV-A 节（"All the perturbed inputs along with x itself are concurrently fed into the deployed DNN model"）；Algorithm 1 第 7 行 H ← F_Θ(D_p)。

### 步骤 4：逐副本 Shannon 熵（shannon_entropy）
- 输入：第 n 张扰动图的概率向量 y^(n)。
- 计算：H_n = −Σ_{i=1}^{M} y_i × log₂ y_i（式 2），y_i 为该扰动输入属于类别 i 的概率。
- 输出：标量 H_n，共 N 个。
- 论文出处：式 (2)，第 IV-D 节。

### 步骤 5：熵求和与归一化得到样本分数（mean_entropy_score）
- 输入：{H_1, …, H_N}。
- 计算：先求和 H_sum = Σ_{n=1}^{N} H_n（式 3），再归一化 H = (1/N) × H_sum（式 4）；论文明确"H is regarded as the entropy of one incoming input x"，并且"H_sum standing for the chance the input x being trojaned. Higher the H_sum, lower the probability the input x being a trojaned input"。
- 输出：单个标量分数 H ∈ [0, log₂M] 量级。
- 论文出处：式 (3)、式 (4)，第 IV-D 节。

### 步骤 6：检测边界标定（gaussian_quantile_threshold）
- 输入：良性输入的熵分布（用 D_test 上重复步骤 1–5 得到的 H 值集合）。
- 计算：论文假定良性输入熵服从正态分布（"It is reasonable to assume that such a distribution is a normal distribution"），由良性样本估计均值与标准差；先设定目标 FRR（如 1%），再取该正态分布对应百分位作为检测边界。这一步是离线标定，需在部署后针对**每一个部署模型**单独做（第 VII-C 节强调该边界不是 Neural Cleanse 式的全局设置）。
- 输出：标量 detection boundary。
- 论文出处：第 V-C 节；Algorithm 1 的入参 detection boundary。

### 步骤 7：阈值比较与告警（threshold_flag）
- 输入：待检输入的分数 H 与 detection boundary。
- 计算：若 H ≤ detection boundary，则 trojanedFlag ← Yes，否则为 No（Algorithm 1 第 8–10 行）。
- 输出：布尔判定；论文未定义判定后的具体处置动作（仅说明输入被判为 trojaned，并"very likely"意味着模型被植入后门）。
- 论文出处：Algorithm 1 第 8–10 行；第 IV-A 节。

## 4. 采样与规模控制

论文确实做了抽样与规模实验：

- **样本（扰动副本数 N）**：对每个待检输入生成 N 张扰动图。案例研究（MNIST 方形触发器与 heart 触发器、CIFAR10 trigger b 与 trigger c、GTSRB trigger b）统一取 N = 100（表 III 的 "N" 列、第 V-B 节各小节、Fig. 5 说明中"1000 perturbed images"是图 5 的可视化实验）。开销实验把 N 从 2 变化到 100（第 V-D 节、Fig. 10）；并给出经验结论"setting N = 10 is sufficient"（GTSRB 数据集、trigger b，第 V-D 节）。
- **探针/参考数据量**：从用户留存的 D_test 中随机抽取参考图，每次抽 1 张、共 N 张。论文没有给出 D_test 的最小规模要求，只说明防御方"has held out a small collection of validation samples"（第 IV-B 节）。
- **评测样本量**：每个数据集测试 2000 张良性输入与 2000 张木马输入（第 V-B 节 1)、2)、3) 小节；第 VI-E 节的局部后门同样是 2000 + 2000。
- **层与参数坐标**：论文未使用（方法只看输入与输出 softmax，黑盒）。
- **轮次**：论文未使用（不做跨轮累积；判定是逐输入、单次完成的）。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| N | 每个输入生成的扰动副本数 | 案例研究 N = 100；开销实验 N ∈ [2, 100]；GTSRB + trigger b 经验上 N = 10 已足够 | 表 III "N" 列；第 V-B 节；第 V-D 节、Fig. 10、Fig. 11 |
| FRR | 预设的误拒率，用于确定检测边界 | 1%（主结论）；表 III 另给 3%、2%、1%、0.5%；透明度实验与多触发器实验中预设 0.5% | 表 III；第 V-C 节；第 VI-A 节；表 V（Appendix A）；第 VI-C 节 |
| detection boundary | 由良性熵正态分布的百分位确定 | 随数据集/触发器/模型变化，例如 MNIST 方形触发器 1% FRR 时为 0.026，CIFAR10 trigger b 1% FRR 时为 0.28；透明度实验为 0.10–0.2247 | 表 III；表 V |
| 触发器透明度 | 攻击侧参数，用于鲁棒性评测 | 0%（默认为不透明）、90%、80%、70%、60%、50% | 第 VI-A 节；Fig. 14；表 V |
| α、β（混合权重） | 线性混合系数 | **论文未说明**（只写 superimposing / cv2.addWeighted，图 3、图 4 示例对应等权） | 第 III 节、脚注 2；第 IV-A 节 |
| log 底数 | 熵的底数 | 式 2 写为 log₂ | 式 (2) |
| softmax 概率 y_i | 模型输出的类别概率 | 使用模型 softmax 输出 | 第 II-A 节；第 IV-D 节 |

（第 V-A 节的 batch size、epoch、学习率，如 MNIST batch 128 / epoch 20 / lr 0.001，属于攻击方训练被检模型的设置，不是 STRIP 检测器的超参数。）

## 6. 判定与动作

- **判定规则**：单一标量阈值比较，H ≤ detection boundary 即 trojanedFlag = Yes（Algorithm 1 第 8–10 行）。没有聚类、没有跨轮累积、没有对更新加权或裁剪，也没有加噪。
- **阈值如何得到**：先由用户设定 FRR（例如 1%），在良性输入熵的正态分布上取对应百分位作为边界（第 V-C 节）；FAR 则是木马输入熵大于该边界的概率（第 V-C 节）。论文报告 FRR 与 FAR 之间存在权衡："FAR increases with the decrease of FRR"（第 V-C 节）。
- **实际性能（用于判断可实现性）**：给定 1% FRR，整体 FAR < 1%（摘要、第 V-C 节）；CIFAR10 与 GTSRB 在多数配置下 FAR = FRR = 0%（第 V-C 节、表 III）；浅层 2 层模型上 2% FRR 给 0.45% FAR、1% FRR 给 0.6% FAR、0.5% FRR 给 0.9% FAR（Appendix B）。
- **动作**：论文只产出"输入是/不是木马输入"的标志，并据此提示所部署模型很可能被后门化；**论文未说明**判为木马输入之后是否丢弃该输入、是否阻断服务、是否触发重训或模型替换。
- **一个补充的检测动作（针对自适应攻击）**：在 entropy manipulation（熵操纵）自适应攻击下，木马与干净输入的熵分布变得相似，作者提出改看**干净输入**的熵分布是否偏离正态、以及熵是否整体异常偏高（"It is always more than 3.0"），以此判定模型恶意（第 VI-F 节、Fig. 13）。该检查不依赖木马样本。

## 7. 需要的外部资源

- **用户留存的干净参考数据集 D_test**（held-out samples），不含触发器。规模：论文实验用评测集的 2000 张良性图，以及全局留出集；对最小条数**论文未说明**，只说"a small collection of validation samples"（第 IV-B 节）。
- **已部署的（良性或木马）模型 F_Θ() 及其 softmax 输出**；黑盒访问即可，不需要内部神经元（第 IV-A 节、表 IV）。
- **良性输入的熵统计量**（均值、标准差）或直接可用的 detection boundary，逐模型标定（第 V-C 节、第 VII-C 节）。论文强调 STRIP 不需要参考模型（"STRIP does not need reference model but solely the already deployed (begin/backdoored) model"，第 VII-C 节）。
- **不需要**：触发器知识、木马样本、根数据集（root dataset）、预训练检测器、对齐前后的权重、额外模型副本（并行推理时可选用 N 个模型副本，属可选优化，第 V-D 节）。
- 论文中额外用到的木马样本（每个配置 2000 张）只用于离线评估 FAR/FRR，防御方在威胁模型下并不拥有（第 IV-B 节、第 V-C 节）。

## 8. 计算与存储开销

- 论文报告：在 ResNet20 + GTSRB + trigger b、batch size 32 下，生成 N = 10 张扰动图耗时 0.1 ms，预测 10 张图耗时 6.025 ms，STRIP 总开销 6.125 ms，原始推理时间 4.63 ms，即"STRIP is 1.32 times longer than the original default inference time"（第 V-D 节）。该实验同时给出检测时延随 N 从 2 到 100 的变化（Fig. 10、Fig. 11）。
- 分析：主要开销来自步骤 3——每个待检输入要做 N 次额外的模型前向传播（加原图的 1 次共 N+1 次），因此耗时近似随 N 线性增长；图像混合开销很小（0.1 ms，且论文指出该步可并行），熵计算是 O(N·M) 的轻量操作。存储开销分析：只需保存 N 张扰动图与 N×M 概率矩阵，以及良性熵分布的均值/标准差两个标量；论文未单独报告内存占用。
- 论文指出判别精度与模型深度相关：模型越深、干净输入准确率越高，STRIP 检测能力越好（Appendix B）。

## 9. 实现时容易错的地方

论文明确强调或给出的边界情况：

1. **判据方向不能写反**：熵越低越可疑，"Higher the H_sum, lower the probability the input x being a trojaned input"（第 IV-D 节），判定条件是 H ≤ boundary 才置 trojanedFlag = Yes。
2. **边界可能出现负值**：MNIST 方形触发器在 FRR = 0.05% 时"the detection boundary value becomes a negative value. Therefore, the FRR given FAR of 0.05% does not make sense, which is not evaluated"（表 III 脚注 1）——实现时需要对边界下界做处理或拒绝该配置。
3. **边界不是全局设定**：它来自每个已部署模型自身的良性熵分布，不能沿用其他模型的值（第 VII-C 节）。
4. **N 的选择方法**：论文建议观察良性熵分布标准差随 N 变化的斜率，斜率变小时取该 N（第 V-D 节、Fig. 11）；GTSRB + trigger b 下 N = 10 足够。
5. **误拒样本的语义**：在浅层模型上被误接收的木马图中，多数已经失去木马效果（10 张里有 6 张无法被劫持到 'horse'），因此这些误接收并不构成攻击者想要的安全问题（Appendix B、Fig. 15）。
6. **触发器大小无关性**：大触发器（Hello Kitty、heart、trigger c）同样能检测，这是与 Neural Cleanse、SentiNet 的差异点（第 V-C 节、第 VI-B 节、第 VII-C 节、表 IV）。
7. **对熵操纵自适应攻击的检测依据是干净样本分布**：干净输入熵分布偏离正态且整体异常偏高（恒大于 3.0）即提示恶意模型（第 VI-F 节）；要落地这一点，部署后必须主动复检干净输入的熵分布，而不是只查木马输入。
8. **论文明确的能力边界**：对 source-label-specific（源标签特定/局部）后门，只有在防御者被允许持有木马样本、离线做熵分布分析时才可能看出差异；在论文威胁模型下 STRIP 无效（第 VI-E 节、第 VIII 节）。非视觉域（文本替换若干词、语音）只是设想，**论文未评测**（第 V-A 节）。

论文没有说清、实现时必须自行决定的地方（逐条）：

- 线性混合权重 α、β 的具体取值未给出（只给 `cv2.addWeighted()` 这一实现线索），也未说明是否对叠加结果做像素截断或归一化；图像数值范围（0–255 或 0–1）未说明。
- 参考图是否**有放回**抽取未说明；是否允许重复、是否要求参考图与待检输入类别不同未说明（第 III 节只说"randomly drawn"）。
- N 没有统一定值，只有"经验上 10 足够"的说法，且该结论仅来自 GTSRB + trigger b。
- 熵的 log 底数在公式中写作 log₂，但论文未讨论不同底数对边界标定的影响。
- 边界标定所需的良性样本条数、标定是否要用与 D_test 相同的数据、是否复用到后续所有轮/所有输入，均未说明。
- 良性熵"服从正态分布"只是合理假设与经验观察，未做正态性检验；偏态分布下百分位法会失真。
- 判定为木马输入后系统该做什么（丢弃、告警、阻断）未定义。
- 未给 FRR/FAR 目标之外的报警策略参数（例如是否允许逐输入自适应边界）。
- 未说明多触发器（第 VI-C、VI-D 节的 10 个触发器）场景下是否需要多套边界，还是共用一条边界。
- 未说明与批处理推理的交互：原图与 N 张扰动图是否同一 batch、batch size 如何影响时延（仅在开销实验中提到 batch size 为 32 的脚注 3）。

## 10. 原文依据

以下引句均逐字复制自论文全文。

1. **支撑步骤 1–3（整体机制：输入无关触发被扰动后预测不变，因此可用强扰动观测随机性）**
   "The key insight is that, regardless of strong perturbations on the input image, the predictions of all perturbed inputs tend to be always consistent, falling into the attacker's targeted class."
2. **支撑步骤 1（参考图从 D_test 随机抽取）与步骤 3（扰动图与 x 一起送入模型）**
   "The perturbation step generates N perturbed inputs {xp1, ......, xpN } corresponding to one given incoming input x. Each perturbed input is a superimposed image of both the input x (replica) and an image randomly drawn from the user held-out dataset, Dtest."
3. **支撑步骤 2（线性混合的具体做法与实现命令）**
   "The perturbation considered in this work is image linear blend—superimposing two images 2. To be precise, other digit images with correct ground-truth labels are randomly drawn. Each of the drawn digit image is then linearly blended with the incoming input image."
4. **支撑步骤 4（熵公式）与步骤 5（归一化）**
   "Starting from the nth perturbed input xpn ∈ {xp1, ......, xpN }, its entropy Hn can be expressed: Hn = − i=M X i=1 yi × log2 yi (2)"
5. **支撑步骤 5（H_sum 与归一化 H 的语义）**
   "Based on the entropy Hn of each perturbed input xpn, the entropy summation of all N perturbed inputs {xp1, ......, xpN } is: Hsum = n=N X n=1 Hn (3) with Hsum standing for the chance the input x being trojaned."
6. **支撑步骤 6（用良性熵正态分布的百分位确定边界，FRR 先设定）**
   "Firstly, FRR, e.g., 1%, of a detection system is determined. Then the percentile of the normal distribution is calculated. This percentile is chosen as the detection boundary."
7. **支撑步骤 7（阈值比较产生布尔判定）与步骤 7 的 FAR 语义**
   "Consequentially, the FAR is the probability that the entropy of an incoming trojaned input is larger than this detection boundary."
8. **支撑第 8 节的开销（N 次额外前向传播与时间倍率）**
   "To be speciﬁc, processing time—generating N = 10 perturbed images—takes 0.1ms, while predicting 10 images takes 6.025ms 3. In total, STRIP detection overhead is 6.125ms, whereas the original inference time without implementing STRIP is 4.63ms."

```json
{
  "key": "gao2019strip",
  "method": "STRIP: run-time detection of trojaned inputs by strong intentional perturbation (linear blending with held-out clean images) and Shannon entropy of the predicted softmax class distribution",
  "stages": ["client_pre_train", "outside_training"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "sample_reference_images",
      "operator": "sample_reference_batch",
      "input": "user held-out clean test dataset D_test; input image x to be inspected",
      "output": "N reference images {x_1^t,...,x_N^t} drawn at random from D_test",
      "params": {"N": "100 in the case studies (Table III), 10 found sufficient for GTSRB (Sec V-D)", "replacement": "论文未说明"},
      "source": "Algorithm 1 lines 3-6; Sec IV-A; Sec III"
    },
    {
      "step": "linear_blend_perturbation",
      "operator": "linear_blend",
      "input": "x replicated N times and the N sampled reference images, shape 28x28x1 (MNIST) or 32x32x3 (CIFAR10/GTSRB)",
      "output": "perturbation set D_p = {x_1^p,...,x_N^p}",
      "params": {"alpha": "论文未说明", "beta": "论文未说明", "implementation": "cv2.addWeighted() (Sec III, footnote 2)"},
      "source": "Sec IV-A; Algorithm 1 line 5; Sec III footnote 2"
    },
    {
      "step": "forward_pass_perturbed_set",
      "operator": "model_forward_softmax",
      "input": "N perturbed images D_p plus the original image x",
      "output": "N class-probability vectors y^(n) in R^M (softmax) and the predicted label z of x",
      "params": {"batch_size": "32 in the overhead experiment (Sec V-D footnote 3); 论文未说明 otherwise"},
      "source": "Sec IV-A; Algorithm 1 line 7; Sec II-A"
    },
    {
      "step": "per_perturbation_entropy",
      "operator": "shannon_entropy",
      "input": "probability vector y^(n) of the n-th perturbed image",
      "output": "scalar H_n for n = 1..N",
      "params": {"log_base": "2 (Eq 2)", "num_classes_M": "10 (MNIST, CIFAR10), 43 (GTSRB) per Table I"},
      "source": "Eq (2), Sec IV-D"
    },
    {
      "step": "sum_and_normalize_entropy",
      "operator": "mean_entropy_score",
      "input": "{H_1,...,H_N}",
      "output": "scalar score H = (1/N) * sum_n H_n",
      "params": {},
      "source": "Eq (3), Eq (4), Sec IV-D"
    },
    {
      "step": "calibrate_detection_boundary",
      "operator": "gaussian_quantile_threshold",
      "input": "entropy scores H computed on benign held-out inputs with the deployed model",
      "output": "scalar detection boundary",
      "params": {"distribution": "normal, assumed (Sec V-C)", "preset_FRR": "1% main; also 3%, 2%, 1%, 0.5% in Table III; 0.5% in Sec VI-A / Sec VI-C / Table V"},
      "source": "Sec V-C; Algorithm 1 argument detection boundary; Sec VII-C"
    },
    {
      "step": "flag_incoming_input",
      "operator": "threshold_flag",
      "input": "H of the incoming input and the detection boundary",
      "output": "boolean trojanedFlag (Yes/No)",
      "params": {"rule": "trojanedFlag = Yes if H <= detection boundary"},
      "source": "Algorithm 1 lines 8-10; Sec IV-A"
    },
    {
      "step": "auxiliary_clean_distribution_check",
      "operator": "clean_entropy_distribution_audit",
      "input": "entropy scores of clean inputs collected after deployment",
      "output": "verdict that the model is malicious if clean-input entropy deviates from normal or is abnormally high (always > 3.0)",
      "params": {"threshold": "> 3.0 observed for the entropy-manipulation attack (Sec VI-F, Fig. 13)"},
      "source": "Sec VI-F, Fig. 13"
    }
  ],
  "sampling": [
    {"what": "probes", "how": "N perturbed replicas per incoming input, each blend uses one randomly drawn held-out image", "size": "N = 100 in the case studies (Table III); N swept from 2 to 100 for overhead (Fig. 10); N = 10 judged sufficient for GTSRB trigger b (Sec V-D)"},
    {"what": "samples", "how": "benign held-out inputs used to estimate the normal entropy distribution and the detection boundary", "size": "2000 benign inputs per configuration in the case studies (Sec V-B); minimum size of D_test 论文未说明"},
    {"what": "samples", "how": "trojaned inputs used only offline to evaluate FAR, not available to the defender under the threat model", "size": "2000 trojaned inputs per configuration (Sec V-B, Sec V-C)"},
    {"what": "clients", "how": "论文未使用", "size": "论文未使用"},
    {"what": "layers", "how": "论文未使用 (black-box, softmax outputs only)", "size": "论文未使用"},
    {"what": "coordinates", "how": "论文未使用", "size": "论文未使用"},
    {"what": "rounds", "how": "论文未使用 (per-input decision, no cross-round accumulation)", "size": "论文未使用"}
  ],
  "resources": [
    "deployed DNN model F_Θ() with softmax output; black-box access is enough (Sec IV-A, Table IV)",
    "user held-out clean test dataset D_test without triggers; 'a small collection of validation samples' (Sec IV-B), exact minimum 论文未说明",
    "benign entropy statistics (mean and standard deviation) or a directly usable per-model detection boundary (Sec V-C, Sec VII-C)",
    "optional N model replicas for parallel prediction (Sec V-D)"
  ],
  "actions": ["filter_samples", "report_only"],
  "dominant_cost": "N extra forward passes of the deployed model per inspected input; reported total 6.125 ms vs 4.63 ms baseline (1.32x) with N = 10 on ResNet20/GTSRB, of which 6.025 ms is prediction and 0.1 ms is generating the N = 10 perturbed images (Sec V-D). 分析：cost grows about linearly with N, plus O(N*M) entropy computation.",
  "underspecified": [
    "linear blend coefficients alpha and beta are never stated numerically; only 'superimposing two images' and the cv2.addWeighted() command are given (Sec III, footnote 2)",
    "whether reference images are drawn with or without replacement, and whether they may repeat or share the class of x (Sec III just says 'randomly drawn')",
    "minimum size of the held-out dataset D_test needed for boundary calibration (Sec IV-B only says a small collection)",
    "how many benign inputs are needed to fit the normal distribution and whether the same D_test is reused for every incoming input and every round",
    "no normality test is defined; the normal-distribution assumption for benign entropy is only asserted and observed empirically (Sec V-C)",
    "pixel value range, rounding/clipping after blending, and channel handling are not specified",
    "the action taken after trojanedFlag = Yes (drop input, raise alert, block service) is not defined",
    "whether one shared detection boundary suffices for the multiple-trigger scenarios (Sec VI-C, Sec VI-D) is not stated",
    "1.32x overhead is measured with batch size 32 on ResNet20/GTSRB only; interaction with other batch sizes and parallel replicas is not quantified (Sec V-D)",
    "for source-label-specific (partial) backdoors, detection requires offline analysis with access to trojaned samples, which contradicts the threat model; no run-time rule is given (Sec VI-E, Sec VIII)",
    "non-vision domains (text word replacement, speech) are only suggested and never evaluated (Sec V-A)"
  ],
  "quotes": [
    {"supports": "step 1-3: the core mechanism that input-agnostic triggers keep predictions constant under strong perturbation", "text": "The key insight is that, regardless of strong perturbations on the input image, the predictions of all perturbed inputs tend to be always consistent, falling into the attacker's targeted class."},
    {"supports": "step 1 and step 3: perturbed inputs are superimposed with an image randomly drawn from the user held-out dataset and fed to the deployed model", "text": "The perturbation step generates N perturbed inputs {xp1, ......, xpN } corresponding to one given incoming input x. Each perturbed input is a superimposed image of both the input x (replica) and an image randomly drawn from the user held-out dataset, Dtest."},
    {"supports": "step 2: linear blend implementation detail", "text": "The perturbation considered in this work is image linear blend—superimposing two images 2. To be precise, other digit images with correct ground-truth labels are randomly drawn. Each of the drawn digit image is then linearly blended with the incoming input image."},
    {"supports": "step 4: per-perturbation Shannon entropy formula (Eq 2)", "text": "Starting from the nth perturbed input xpn ∈ {xp1, ......, xpN }, its entropy Hn can be expressed: Hn = − i=M X i=1 yi × log2 yi (2)"},
    {"supports": "step 5: entropy summation over the perturbation set and its interpretation (Eq 3)", "text": "Based on the entropy Hn of each perturbed input xpn, the entropy summation of all N perturbed inputs {xp1, ......, xpN } is: Hsum = n=N X n=1 Hn (3) with Hsum standing for the chance the input x being trojaned."},
    {"supports": "step 6: detection boundary is the percentile of the benign entropy normal distribution at the preset FRR", "text": "Firstly, FRR, e.g., 1%, of a detection system is determined. Then the percentile of the normal distribution is calculated. This percentile is chosen as the detection boundary."},
    {"supports": "step 7: threshold semantics and where FAR comes from", "text": "Consequentially, the FAR is the probability that the entropy of an incoming trojaned input is larger than this detection boundary."},
    {"supports": "section 8 cost: N extra predictions and the measured 1.32x time overhead", "text": "To be speciﬁc, processing time—generating N = 10 perturbed images—takes 0.1ms, while predicting 10 images takes 6.025ms 3. In total, STRIP detection overhead is 6.125ms, whereas the original inference time without implementing STRIP is 4.63ms."}
  ]
}
```
