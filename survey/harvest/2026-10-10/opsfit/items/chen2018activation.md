## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：`partial`（部分可表达）。** 12 步里 7 步能直接落地，3 步缺可复用算子，1 步缺数据取法。更重要的是：这条流水线在结构上根本不是一条联邦流水线——它假设防御方自己训练可疑模型、自己持有全部训练数据、并且能反复重训，pipeline 里完全没有出现 `received` / `uploads` / `aggregate` / `outgoing` 这些联邦坐标，唯一与运行时对接的两个点是"逐样本隐状态"和"对 `samples` 的改/删"。

逐步对照：

| 步 | 归类 | 依据（关键疑点） |
|---|---|---|
| 1 训练可疑模型 | outside | 普通训练/离线准备，catalog 不需要也不提供训练算子 |
| 2 取最后隐层激活并展平 | runtime_data | `model.hidden(samples, layer, pool)` + coordinate `samples/hidden_state/sample`，一层一层对上 |
| 3 按类别分段 | compose | 标签比较 + 布尔索引；`sampling.stratified` 会按类截断到 `per_group`，不能直接用 |
| 4 ICA 降维 | missing_op | catalog 只有 `transform.pca`；ICA ≠ PCA，不能替代 |
| 5 2-means | op | `cluster.kmeans(X, k=2)` |
| 6 ExRe 排除式重训判定 | missing_op | 需要"去掉子集→重训→重新分类→打分"的单元；`probe.fit_logistic` 只是线性探针，替代不了重训 DNN |
| 7 簇大小比判定 | compose | 计数/除法/比较；`robust.largest_gap_threshold` 是找一维切点，不是按比例判 |
| 8 轮廓系数判定 | op | `cluster.distances` + `cluster.silhouette`，k=2 满足"≥2 簇" |
| 9 sprite 摘要 | compose（数据可疑） | pad/cat/mean 都是普通张量运算，但 coordinate 里没有"原始图像像素"这一取法 |
| 10 LDA 主题摘要 | missing_op | `text.*` 只有分词/哈希词袋/留一困惑度；无主题模型，也无词干化 |
| 11 重标注源类并续训 | runtime_action | `edit_samples`（对 `samples` 的编辑）；续训是普通训练 |
| 12 删毒样本重训 | runtime_action | `mask_samples`；重训同样是普通训练 |

两点结构性观察：

- **运行时只给"读"，不给"训"。** `model.*` 句柄（`losses/hidden/activations/per_sample_gradients/logprob/generate/lora`）全是前向/反向检查接口；catalog 里的 `update.*` 是裁剪与加噪、`states.*` 是状态代数，**没有任何优化器或训练循环算子**。而本方法有两处必须真正重训（步骤 6 的排除式重训、步骤 11/12 的修复重训）。这在 vocabulary 里恰好落在"普通本地训练"（`local_training` 能力、`trace`/`gradients`/`local_update` 制品）这一 `outside` 范畴：训练"存在"，但没被包成可调用的检测子程序。
- **detection 部分和库现有路线不同族。** catalog 的 `cluster.majority_cluster` / `density_clusters` 走的是 FLAME/FreqFed 那条"HDBSCAN 找多数稠密簇"的路；AC 走的是"每类固定 k=2 + 轮廓阈值"。两条路都能表达，但 AC 必须用 `kmeans` + `silhouette`，不能拿 `majority_cluster` 顶替（阈值语义和簇数假定都不同）。

---

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用的（别的方法也会用，值得补成算子/接口）：**

1. **排除式重训验证（`classifier_training` 族）** —— 最通用的一块。"去掉候选子集 → 重训 → 重新分类 → 比较前后行为"是数据消融、影响函数、unlearning 检测、leave-one-out 归因的共同骨架，AC 只是把它当成 ExRe 用。缺的不是某个阈值，而是"训练"这个可复用单元本身。
2. **ICA / 盲源分离投影（`transform`，或按"矩阵分解"归 `spectral_decomposition`）** —— 任何在激活/表征层面做检测（latent-space 分析、表征解耦、成分分离）的方法都要用；`transform.pca` 不能顶替，因为 PCA 找的是最大方差方向，ICA 找的是统计独立方向。
3. **LDA 主题摘要 + 词干化（`probabilistic_model` / `text`）** —— 只要防御流程里有"人核验文本簇"就会用到；词干化是通用预处理，`text.split_words` 只到分词。
4. **原始（图像/多模态）样本张量的 coordinate** —— 这严格说是数据接口缺口而不是算子缺口，但任何可视化、多模态审计、像素级分析都缺它；目前 `samples` 只列了 manifest/text/hidden_state/activation/loss/gradient/logprob。
5. **网格拼图 / 簇内平均图** —— 只值几行 `pad/cat/mean`，属于"通用但太小"，不建议做成算子。

**这篇论文特有的（不要做成通用算子，用 compose 编排即可）：**

- **AC 的判据组合与阈值**：每类"ICA(10) → 2-means → 轮廓系数 ∈ [0.10, 0.15] → 相对大小 ≤ p"这一整套串联逻辑，以及 0.10–0.15、p 这些经验值。尤其 `p`（预期最大投毒比例）论文没给默认值，属于使用者先验，是**参数问题不是算子问题**；`cluster.silhouette` 返回的标量拿去和阈值比，一行比较就够。
- **用轮廓系数当"簇是否可分"的判据、再用 ExRe 去纠正误报**——这个"先聚类后消融验证"的编排是 AC 的特色，但每一块零件都是通用件。
- 步骤 6 参数 `T=1` 的语义（阈值还是重复次数）论文侧没有说明，属于实现时要澄清的疑点，不影响算子归类。

---

```json
{
  "key": "chen2018activation",
  "steps": [
    {
      "n": 1,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "在（可能被投毒的）训练集上训练一个普通分类器，是论文前提与离线准备，不是防御计算本身。catalog 里没有任何训练/优化器算子，但训练在 vocabulary 里是客户端既有能力（local_training + trace/gradients/local_update 制品），所以归 outside，不构成缺口。"
    },
    {
      "n": 2,
      "class": "runtime_data",
      "uses": ["samples/hidden_state/sample", "model.hidden"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "coordinate samples/hidden_state/sample（via model_handle）就是逐样本隐藏状态，模型句柄方法 model.hidden(samples, layer, pool) 指定最后一层并取一个向量；展平/reshape 是普通张量运算。无需新算子。"
    },
    {
      "n": 3,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "按预测标签做布尔掩码 + 行索引即可切出 N_i×d 的 A[i]，全是普通张量运算。疑点：catalog 里最接近的 sampling.stratified(groups, per_group, rng) 只给每类至多 per_group 个索引，会把类截断，不能用来构造完整的分组矩阵，因此不算 op。"
    },
    {
      "n": 4,
      "class": "missing_op",
      "uses": [],
      "missing_name": "ica_projection",
      "missing_family": "transform",
      "missing_io": "输入：A (N×d) 张量、n_components=k（此处 10）、可选 seed/最大迭代/容差；输出：(scores (N×k), unmixing 矩阵 (k×d))，接口与 transform.pca 对齐。",
      "note": "独立成分分析（白化 + 非高斯性最大化）在 catalog 里不存在，只有 transform.pca。ICA 与 PCA 目标不同（独立 vs 不相关/最大方差），不能互相替代。按'学一个线性投影做降维'归 transform 族；若把 spectral_decomposition 理解为一切矩阵分解族，也可归入该族，这是归类上的疑点而非能力上的疑点。另需注意 ICA 的分量顺序与符号有歧义，复现性要靠固定 seed。"
    },
    {
      "n": 5,
      "class": "op",
      "uses": ["cluster.kmeans"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "cluster.kmeans(X, k=2) 直接给出标签与中心，满足'2-means'。catalog 用 k-means++ 初始化 + restarts，与论文的随机初始化只是参数/实现差异，按题意算 op。seed 固定后可复现。"
    },
    {
      "n": 6,
      "class": "missing_op",
      "uses": [],
      "missing_name": "exclude_subset_retrain_reclassify",
      "missing_family": "classifier_training",
      "missing_io": "输入：训练集 (X, Y) 或样本索引、待排除子集索引 S（候选毒簇）、待检验模型及其训练配置（结构、训练步/epochs、重复次数 T、seed）；输出：(重训后的模型, S 中每个样本的新预测、被重判为源类 C 的比例 l/p、源类标签 C、毒/干净判定)。",
      "note": "ExRe：把候选簇的样本从训练集移除后重训，再看这些被排除的样本有多大比例被重新判到源类 C。catalog 里 probe.fit_logistic 只拟合一个线性探针，无法替代'按子集重训 DNN 再分类'。运行时也不提供训练算子（model.* 只做前向/反向检查，update.*/states.* 只做状态裁剪与代数），所以这是算子缺口：训练本身是运行时既有的普通能力，但没有任何单元把'排除→重训→重分类→打分'打包起来。参数 T=1 含义论文未说明（阈值或重复次数），需澄清。"
    },
    {
      "n": 7,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "只需两个簇的计数：较小簇占该类样本的比例与阈值 p 比较（接近 1 视为该类别未被投毒），再据此挑出毒簇。全是计数、除法、比较，几行张量运算。catalog 无'簇大小比'算子；robust.largest_gap_threshold 是给一维数值找最大间隔切点，不按比例判定，不能替代。p 是论文未给默认值的先验参数，属参数问题。"
    },
    {
      "n": 8,
      "class": "op",
      "uses": ["cluster.distances", "cluster.silhouette"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "先用 cluster.distances 在 red_i 上算距离矩阵，再 cluster.silhouette(D, labels) 取平均轮廓系数；k=2 满足其'>=2 簇'要求，阈值 0.10-0.15 只是一次标量比较。silhouette 会忽略噪声标签 -1，而 k-means 不产生噪声，无影响。"
    },
    {
      "n": 9,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把簇内图像按网格 pad/reshape/cat 拼成 sprite、再按样本维求均值，都是普通张量运算，不需要新算子。疑点（数据而非算子）：vocabulary 的 samples 只列出 manifest/text/hidden_state/activation/loss/gradient/logprob 这些取法，没有'原始图像张量'这一 coordinate；若样本是图像，这一步拿不到输入，需要补一个数据取法，届时应改判 needs_runtime。"
    },
    {
      "n": 10,
      "class": "missing_op",
      "uses": ["text.split_words"],
      "missing_name": "lda_topic_summary",
      "missing_family": "probabilistic_model",
      "missing_io": "输入：一个簇的样本文本 list[str]（内部先分词/词干化）或已分词的 token 计数矩阵、n_topics=2、n_words_per_topic=6；输出：每个主题的 top 词表 list[list[str]]（可选每文档主题分布）。",
      "note": "catalog 的 text 族只有 split_words、hashed_bag_of_words、leave_one_out/outlier_words（困惑度删除判定），没有主题模型；LDA 需要变分或 Gibbs 推断，是可复用但缺失的单元。另外'先词干化'也没有对应函数（无英文词干/词形还原），需并入该单元或另补一个小预处理。若把该算子归 text 族而非 probabilistic_model 族也说得通，这里按'生成式概率主题模型'归类。"
    },
    {
      "n": 11,
      "class": "runtime_action",
      "uses": ["edit_samples"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把毒样本的标签改成源类 C 属于对 samples 制品的编辑，vocabulary 允许的动作正是 mask_samples/edit_samples 里的 edit_samples。其后的'继续训练 14 epochs'是普通训练（outside 范畴），catalog 无训练算子但不影响本步的归类：本步的防御语义是'改样本'。语义上这里改的是防御方自己持有的那份数据，而 samples 在 vocabulary 中定义为 client 侧，属于跨场景套用，需要使用者自行对齐。"
    },
    {
      "n": 12,
      "class": "runtime_action",
      "uses": ["mask_samples"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "删掉毒样本等价于对 samples 做掩码，直接对应 mask_samples 动作（之后 80 epochs 从头重训仍是普通训练）。步骤 11/12 是同一修复动作的两个变体（改标签 vs 剔除），都落在 vocabulary 的动作集合内。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "步骤 4 缺少 ICA（独立成分分析）降维单元，catalog 只有 transform.pca，二者目标不同不能互相替代，因此'每类先降维到 10 维'这一步无法由现有算子完成。",
    "步骤 6 的 ExRe 需要'排除候选子集→重训→重新分类→按比例打分'这一可复用单元（classifier_training 族），catalog 与运行时都不提供；模型句柄只暴露前向/反向检查（losses/hidden/activations/per_sample_gradients/logprob/generate/lora），update.*/states.* 只做状态裁剪与代数，没有任何训练或优化器算子，重训只能落在运行时既有的普通本地训练上，无法由算子库组合出来。同一缺口也让步骤 11/12 的修复重训无法作为算子被调用。",
    "步骤 10 缺少主题模型（LDA）摘要单元，且没有词干化函数，簇内文本摘要无法产出。",
    "步骤 9 缺数据来源：samples 的 coordinate 里没有原始图像/多模态张量的取法（只有 manifest/text/hidden_state/activation/loss/gradient/logprob），sprite 拼图与簇内平均图拿不到输入。",
    "整体上该方法是集中式、单模型、需反复重训的离线分析流程（stages 为 client_post_train / server_post_aggregate / outside_training），与联邦 LoRA 运行时的 received/uploads/aggregate/outgoing 坐标体系不对应，只能作为旁挂的模型侧诊断插件，无法作为联邦防御流水线端到端执行。"
  ]
}
```
