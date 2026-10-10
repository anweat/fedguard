## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：可以表达绝大部分，但整体只能算 `partial`。** 14 步的归类是：6 步 `op`（3、4、6、10、11、12）、1 步 `runtime_data`（2）、6 步 `compose`（1、5、7、8、9、13）、1 步 `needs_runtime`（14）。检测主干（1–13）不需要任何新算子。

几点值得先说明：

- **catalog 明显是按这篇论文造的。** `sequential.lbfgs_hvp` 的说明直接写 “as used by FLDetector”，`cluster.gap_statistic_k` 写 “as FLDetector uses it”，`sequential.window_mean`、`states.delta`、`states.stack/flatten`、`cluster.kmeans` 也都逐一对得上，所以第 4、6、10、11、12 步是干净的单算子命中，第 3 步的四条聚合规则也各自有现成函数。
- **不需要任何 `via: model_handle` 的 coordinate。** FLDetector 是纯服务器侧方法：它只在“上传向量 + 服务器自己的跨轮记录”上做线性代数，不做前向/反向，也不碰客户端数据。它要的数据是 (a) 本轮每个客户端的上传（`uploads/factor_delta/client` + `uploads/roster/client` 定名单）、(b) 每轮的全局模型与聚合更新（`aggregate/result/model` 与聚合结果，跨轮由 `history/features/round` 承载）、(c) 当前轮号。(a)(b) 词表都有，(c) 没有专门 coordinate，但可从 history 的轮次数推出，属小含糊点。
- **关键不确定点：跨轮保存逐客户端上传张量。** `history/features/round` 只说“此前各轮的特征”，没有明说保留 n×p 的逐客户端上传。第 2、4、7 步都依赖它。我按“history 是通用跨轮容器”判为可表达；如果实际只保留聚合级历史，这三步会一起变成 `needs_runtime`，这是整条流水线最脆的一环。
- **语义空间是代理。** 运行时以 LoRA 因子为制品，展平后 ΔW、ΔG 位于因子空间而非论文的全参数空间，`lbfgs_hvp` 照样能算，但那是论文 Hessian 的代理；同理 `robust.trimmed_mean`/`coordinate_median` 在因子坐标上做，与在乘积空间（`uploads/product_delta/client` 只按 Gram 不展开）做不等价。
- **第 3 步的 Krum 有参数缺口**：catalog 只给 `geometry.krum_scores`（打分），选人还要 argmin 或取最低 m 个再平均，并且需要论文里假定的 f，流水线没给。
- **第 14 步是唯一的硬缺口。** “剔除”可做（`select_and_weight` + `aggregate/weights/client`），但“丢弃当前全局模型、排除客户端、从该轮起重训预先设定的若干轮”要求运行时能重启/回放整个联邦训练循环，运行时只暴露单轮的聚合、加权、下发动作，没有这个入口。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**真正缺的只有一项，而且是通用能力缺口，不是这篇论文特有的。**

- **通用（`needs_runtime`）：训练循环的重启/重训控制。** 任何“检测到就丢弃当前全局模型、排除部分客户端、重跑若干轮”的排除式/回滚式防御，以及任何需要服务器控制客户端准入与轮次调度的场景，都会撞到同一堵墙。FLDetector 只是把这条通用需求绑上了自己的触发条件（“本轮至少检出 1 个恶意就触发”“重训固定轮数”）。
- **论文特有的部分反而没有产生缺口。** FLDetector 的特有计算——用 (Δw, Δg) 的 L-BFGS 二次模型做 HVP、按 `g_i^{t−1} + Ĥ(w^t−w^{t−1})` 逐客户端预测、gap statistic 选 k 后二聚类取高分簇——已经被 catalog 里两个明确标注 FLDetector 的算子覆盖，其余落在普通张量运算里。所以这篇论文**不要求任何新的通用算子**（`missing_op` 为空）。
- **边界项（我判成 `compose`，因此不算缺失，但值得记录为未来的通用候选）**：(i) 两个 n×p 矩阵的逐行配对 L2 距离（第 8 步）属 `distance_geometry` 族的通用小单元，多个方法会比较“预测向量 vs 实收向量”，真要做成算子可叫 `paired_row_l2_distance(A, B) -> (n,)`；(ii) L1 归一化（第 9 步）属 `transform` 族的通用小单元。二者当前用几行 torch 就能拼，按规则不升级为 `missing_op`。
- **另一个“通用但目前被覆盖”的点**：跨轮保存逐客户端上传张量与全局模型，是所有时序/信誉类检测方法的共同前提。词表用 `history/features/round` 覆盖了它；若实际实现只有聚合级历史，它会从“已覆盖”变成“通用缺口”，并同时卡住第 2、4、7 步。

```json
{
  "key": "zhang2022fldetector",
  "steps": [
    {"n": 1, "class": "compose", "uses": ["history/features/round"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "只是 t >= start_iteration 的标量比较，不需要任何函数。疑点：当前轮号 t 没有单独 coordinate，只能由 history/features/round 的轮次数或运行时注入的轮次上下文推出；拿到 t 后这一步是零成本控制流。"},
    {"n": 2, "class": "runtime_data", "uses": ["uploads/factor_delta/client", "uploads/roster/client", "history/features/round", "states.stack"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "本轮 n 个上传由 uploads/factor_delta/client 直接提供（配合 uploads/roster/client 确定名单与顺序），states.stack 把每个客户端的 state 展平堆成 (n,p)。上一轮的 G^{t−1} 取自 history/features/round——该 coordinate 只写“此前各轮的特征”，是否保存逐客户端上传张量是全局最大疑点；若只留聚合级历史，第 2/4/7 步会一起变成 needs_runtime。"},
    {"n": 3, "class": "op", "uses": ["states.weighted_average", "geometry.krum_scores", "robust.trimmed_mean", "robust.coordinate_median", "aggregate/weights/client"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "四条规则都有现成函数：FedAvg=states.weighted_average（说明即 FedAvg in factor space）、Trimmed-Mean=robust.trimmed_mean、Median=robust.coordinate_median（需先把 n 个 state 展平成 (n,p)）、Krum=geometry.krum_scores。Krum 只负责打分，还要 argmin（或取最低 m 个再平均）才能出结果，属极小拼接；且 Krum 需要 f，流水线未给该参数。疑点：坐标式中位数/截尾均值在 LoRA 因子空间做与在乘积空间做不等价。若按运行时动作口径看，等价物是 select_and_weight + aggregate/weights/client。"},
    {"n": 4, "class": "op", "uses": ["states.delta", "aggregate/result/model", "history/features/round"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "Δw = w^t − w^{t−1} 与 Δg = g^t − g^{t−1} 各调用一次 states.delta（state - base，按键同形状逐项相减）。前提是服务器能读到本轮与上一轮的 aggregate/result/model 以及两轮的聚合更新，跨轮部分落在 history。这里的 w 是服务器侧全局模型，不是客户端侧的 received/change_since_last/module。"},
    {"n": 5, "class": "compose", "uses": ["history/features/round"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "缓冲维护本身没有算子：一个列表 append、取最后 N 项（论文要求不含当前轮）、torch.stack 成 (p,N) 即可。catalog 里 sequential.window_mean 只做“对 history 取均值”，不负责窗口缓冲，故不算 op。"},
    {"n": 6, "class": "op", "uses": ["sequential.lbfgs_hvp"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "签名 (dW, dG, v) 与说明（as used by FLDetector；dW/dG 为 (p,N) 的相邻轮差、oldest first）与本步完全对应，v = w^t − w^{t−1} 直接传入。疑点：展平发生在 LoRA 因子空间，p 是因子参数维度而非论文的全参数维度，得到的 HVP 是因子空间代理（可算，但语义上是代理）。"},
    {"n": 7, "class": "compose", "uses": ["states.flatten", "states.unflatten", "states.add"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "预测式 ĝ_i = g_i^{t−1} + Ĥv 就是把同一个共享的 p 维 HVP 广播加到每个客户端上一轮更新上：可按客户端 states.unflatten(vector, like=g_i) 后 states.add(g_i, hvp)，也可把 n 个 state 用 states.stack 堆成 (n,p) 后做一行广播加法。没有专门算子，但只用到普通加法，不需要新计算单元。仅对 t−1 与 t 都在名单里的客户端有定义，roster 对齐属索引操作。"},
    {"n": 8, "class": "compose", "uses": [], "missing_name": "", "missing_family": "", "missing_io": "", "note": "逐元素相减再按行取 L2 范数（torch.norm(dim=1)）即可。catalog 里 cluster.distances 与 geometry.pairwise_sq_distances 只给同一矩阵内部的两两距离，geometry.distance_to 是“所有行到同一个参考向量”且文档为空，都无法直接做两个 n×p 矩阵的逐行配对距离，按规则不记为 op。"},
    {"n": 9, "class": "compose", "uses": [], "missing_name": "", "missing_family": "", "missing_io": "", "note": "d / d.abs().sum() 一行完成。transform.l2_normalize 是 L2 归一化，名字相近但范数不同，不能替用；catalog 里也没有 L1 归一化算子。"},
    {"n": 10, "class": "op", "uses": ["sequential.window_mean"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "把 history 换成过去各轮的 d̂（每轮 (n,)），length=N，函数语义正是“对最后 length 项求均值”，与 s_i^t 定义一致。疑点：若各轮参与客户端集合不同，需先按 roster 对齐再平均（少量取索引操作）。"},
    {"n": 11, "class": "op", "uses": ["cluster.gap_statistic_k"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "函数说明直接写 as FLDetector uses it：min-max 缩放 + uniform 参考样本 + 比较 log 簇内离散度，返回满足 Gap(k) >= Gap(k+1) − s(k+1) 的最小 k，与 K=10、B=20 对应。疑点：参考样本随机种子在签名里固定（seed=0），论文是每轮重新采参考分布，属随机性/参数差异而非能力差异；返回值的边界情形（无 k 满足）文档被截断，需实测。"},
    {"n": 12, "class": "op", "uses": ["cluster.kmeans"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "cluster.kmeans(X, k=2, seed, iters, restarts) 返回 (labels, centers)，把一维 s 整理成 (n,1) 后传入即可。仅在 k̂>1 时执行属控制流，不影响归类；k̂=1 时按论文不产生恶意簇。"},
    {"n": 13, "class": "compose", "uses": ["cluster.kmeans"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "用第 12 步的 labels 做两次“按簇取索引 + 求均值”，再比较两个均值取较大者作为恶意簇。catalog 的 cluster.majority_cluster 是按“包含多数点”选密集簇，判据不同（多数 vs 均值更高），不能替用。k̂>1 保证两簇非空；均值并列时如何取舍需自行约定。"},
    {"n": 14, "class": "needs_runtime", "uses": ["select_and_weight", "aggregate/weights/client"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "“剔除”这一半可表达：聚合名单与权重对应 select_and_weight（uploads 与 aggregate 的 modified_by），名单/权重从 aggregate/weights/client 读取。做不到的是“重启训练”：一旦本轮至少检出 1 个恶意客户端，就要丢弃当前全局模型、排除这些客户端并从该轮起重训预先设定的若干轮。运行时只暴露单轮的 transform_received / transform_update / select_and_weight / replace_global / transform_broadcast，没有训练循环控制、没有回滚/重训/回放接口，也没有“强制排除客户端并重跑若干轮”的入口，故整步归 needs_runtime。"}
  ],
  "expressible": "partial",
  "blocking": ["运行时没有训练循环的重启/重训能力：第 14 步要求检测到恶意客户端后丢弃当前全局模型、排除这些客户端并从该轮起重训固定轮数，而运行时只有单轮的聚合、加权与下发动作，无法驱动或回放整个联邦训练循环"]
}
```
