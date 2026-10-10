## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：可以整体表达（full）。** 10 步里没有一步需要 catalog 之外的新通用算子，也没有一步需要运行时拿不到的数据或做不了的动作。

Krum 的计算内核（第 4–7 步：平方距离 → 每行取 n−f−2 近邻 → 求和 → 取最小）在 catalog 里被三个函数直接覆盖：`geometry.pairwise_sq_distances`、`geometry.krum_scores`、`sampling.top_k`。其中 `geometry.krum_scores` 的说明写的是 "for each row, the sum of squared distances to its n - f - 2 nearest other rows. Lower is more central. Needs n >= f + 3"，与论文的 s(i) 定义逐字对应，属可确认的 op（不是名字相似）。第 8 步"把被选向量当作聚合结果"落在 vocabulary 的 `select_and_weight`（`uploads`、`aggregate` 的 modified_by），第 9 步多出来的"删掉再重算"只是 m 次循环，属普通控制流。第 1、2、10 步（广播 / 本地训练 / 服务器 SGD）是所有 FL 方法共有的骨架，不计入防御计算。

数据面：服务器侧每份上传可由 `uploads/factor_delta/client` 或 `uploads/product_delta/client` 读出（低秩场景不必展开 d 维向量），缺席者由 `uploads/roster/client` 得知，名单与权重落在 `aggregate/weights/client`。因此第 3 步的零填充和后续距离在 LoRA 因子上同样成立：`||M_i − M_j||² = G_ii + G_jj − 2G_ij`，G 由 `lowrank.gram` 给出。

不影响表达性、但影响复现的细节：

- 论文的距离定义在 d 维参数/梯度向量上，而本运行时的本地更新是 LoRA 因子对，必须先按统一约定 flatten（`states.flatten` 按 key 排序 / `states.stack`），否则各客户端展开顺序不一致会让"距离"失去意义。
- 并列取"标识符最小者"：`sampling.top_k` 的说明是 "ties broken by key order"，key 直接用 worker 标识符且按数值可比时与论文一致；若按字符串排序（"10" < "2"）就会偏离数值序，此时用两行 torch（min + eq + 最小下标）修正即可。
- 前置条件 `n ≥ f+3`（`krum_scores` 自带约束）与 m-Krum 的 `n − m > 2f + 2` 属调用方检查，catalog 不代做。
- 第 3 步把缺席者填 0 后，这些零向量会进入距离矩阵和邻居计数；f 的口径（缺席者是否计入 f）论文没写清，这是算法语义问题，不是运行时缺口。

另外，Krum 的 (α,f)-韧性是论文的证明，不是运行时需要执行的计算；它只影响 f 的取值。

## 2. 缺的东西里哪些是通用的、哪些是这篇论文特有的

没有 blocking 缺口。下面区分的是"库确实没有、本流水线用 compose 兜住"的东西，和"只属于这篇论文"的东西。

**通用的（别的方法也会用，将来值得补，但本流水线不需要）：**

- **逐行 k-近邻下标/邻接**：catalog 只有 `geometry.krum_scores`，它把"取 n−f−2 近邻并求和"写死成固定公式，且**不返回邻居身份**。DnC、Bulyan、RFA 一类以及任何"先建图再筛"的方法都要同一件事（距离矩阵上按行取最小的 k 个下标）。本步用 `torch.topk(-D, k)` 两行即可，故记 compose；若要复用，自然形态是 `per_row_knn_indices(D, k) -> 下标矩阵`，属 distance_geometry 族。
- **带标识符的分数 argmin / argmax（含 tie-break）**：几乎所有 isolate 类规则（Krum、Multi-Krum、排名式选择）都要"取极值并给出 client id"，`sampling.top_k` 已提供这个形态，所以不再算缺。
- **缺席更新填零并按名单对齐**：同步 FL 的 straggler/drop-out 通用问题，目前自己 `zeros + index_copy`，属通用胶水而非通用算子。
- **把低秩因子对拉平成可比向量**：`states.flatten` / `states.stack` 已覆盖，不属缺口。

**这篇论文特有的：**

- **分数 s(i) = 到 n−f−2 个最近邻的平方距离之和**：Krum 独有定义，catalog 已用 `geometry.krum_scores` 收录（论文特有但已存在，所以第 6 步是 op）。这也解释了为什么第 5 步不能记 op：该函数只暴露最终分数，不暴露邻居下标，其它 k 或其它聚合规则无法复用。
- **m-Krum 的"删掉已选 → 在剩余集合上重算分数 → 再选"迭代记账**：属这篇论文（少数继承它的工作会用），循环 + `geometry.krum_scores` + `sampling.top_k` + `states.weighted_average` 即可拼出，不需要新算子。
- **(α,f) 韧性条件 n ≥ 2f+3、n − m > 2f+2**：论文的适用条件，落成调用方前置检查（`krum_scores` 的 n ≥ f+3 已覆盖 Krum 那一半）。

**真正缺的运行能力：无。** 只需与运行时确认两点口径：`select_and_weight` 是否允许"只选一份、权重 1"（从 `aggregate/weights/client` 存在看应可以）；服务器更新用 `states.add(x, F, scale=−γ_t)` 还是 `replace_global` 落账（两者都在，不影响表达）。

```json
{
  "key": "blanchard2017krum",
  "steps": [
    {"n": 1, "class": "outside", "uses": [], "missing_name": "", "missing_family": "", "missing_io": "", "note": "普通下发：把当前参数/全局 LoRA 广播给所有 worker，属所有 FL 方法共有的骨架，不是防御计算。运行时确实提供对应机制（coordinate outgoing/factors/recipient，动作 transform_broadcast），如需记账可记 runtime_action，但不影响表达性。"},
    {"n": 2, "class": "outside", "uses": [], "missing_name": "", "missing_family": "", "missing_io": "", "note": "标准本地 SGD / 无偏梯度估计，论文自己标注为非防御算子（§2）。数据面由 samples/* 与 model handle（model.per_sample_gradients、model.losses）提供，批梯度对应 coordinate gradients/batch_gradient/parameter，LoRA 场景下本地产物是 local_update/factors/module。任何 FL 方法都有这一步，归 outside。"},
    {"n": 3, "class": "compose", "uses": ["states.flatten", "states.stack", "uploads/roster/client"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "catalog 没有‘按名单收齐并补零’的函数。先用 uploads/roster/client 判断缺席者，把收到者的因子差 flatten（states.flatten/states.stack）成 (n,d)，再用 torch.zeros 加逐行赋值 / index_copy 填零即可，属于普通索引赋值，不需要新算子。"},
    {"n": 4, "class": "op", "uses": ["geometry.pairwise_sq_distances"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "与‘平方欧氏距离矩阵’精确匹配，无需自己平方。若手上只有非平方距离，cluster.distances(X,'euclidean') 再平方也可，但不是首选。低秩因子场景：||M_i−M_j||² = G_ii+G_jj−2G_ij，G 由 lowrank.gram 给出（coordinate uploads/product_delta/client 已声明按 Gram 计算，不必展开）。"},
    {"n": 5, "class": "compose", "uses": [], "missing_name": "", "missing_family": "", "missing_io": "", "note": "catalog 无返回邻居下标的函数：geometry.krum_scores 只给最终分数、不暴露邻居身份；sampling.top_k 只作用于 dict 分数而非逐行距离矩阵。用 torch.topk(-D, n-f-2, dim=1) 或 sort 取前 k 列即可（比较＋取索引）。注意：若整条链一次调用 geometry.krum_scores，此步可省略，它把第 4–6 步一并完成。距离并列的打破规则论文未说明。"},
    {"n": 6, "class": "op", "uses": ["geometry.krum_scores"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "定义精确对应：s(i)=到 n−f−2 个最近邻的平方距离和，'Lower is more central'。参数形态不同——输入是 (n,d) 向量矩阵 X 与 f，而非距离矩阵，函数内部自算平方距离；要求 n ≥ f+3，与论文一致，属‘只是参数不同也算’。"},
    {"n": 7, "class": "op", "uses": ["sampling.top_k"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "把分数取负、以 worker 标识符为 key 构造 dict，k=1，即得最小分且并列时取 key 序最小者，与论文‘并列取标识符最小者’一致；‘ties broken by key order’这一说明正是为这类选择写的。疑点：若 key 被按字符串排序（'10'<'2'）会偏离数值序；此时改用 compose（torch.min + eq + 取最小下标）两行即可修正。"},
    {"n": 8, "class": "runtime_action", "uses": ["select_and_weight"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "把第 7 步得到的 i* 对应的那份上传直接当作 aggregate（权重 1）。vocabulary 中 select_and_weight 正是服务器对 uploads/aggregate 做选择与加权的动作，名单与权重落在 coordinate aggregate/weights/client。纯算术上‘取第 i* 行’也可 compose（取索引），但这一步的本质是被 vocabulary 覆盖的服务器选择动作。"},
    {"n": 9, "class": "compose", "uses": ["geometry.krum_scores", "sampling.top_k", "states.weighted_average"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "m-Krum 不是‘一次算分取前 m 名’（论文 §7 明确说那种做法未被证明 (α,f) 韧性），而是每轮删掉已选向量、在剩余集合上重算 s(i) 再取最小，重复 m 次后取平均：m−1 次循环＋top-1＋均值。用现有函数加普通张量运算即可拼出，不需要新的通用算子；最后一律按 1/m 加权在语义上也落在 select_and_weight。约束 n−m > 2f+2 由调用方检查。"},
    {"n": 10, "class": "outside", "uses": [], "missing_name": "", "missing_family": "", "missing_io": "", "note": "常规服务器 SGD 步 x ← x − γ_t·F（论文未给 γ_t 调度）。算术上 states.add(x, F, scale=-γ_t) 精确对应，落账动作是 replace_global；它是所有 FL 方法共有的骨架步，故归 outside。"}
  ],
  "expressible": "full",
  "blocking": []
}
```
