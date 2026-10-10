## 1. 这条流水线整体上能否由现有算子库与运行时表达

**两边的东西几乎不相交。** catalog 全部是**联邦 LoRA 防御侧**的可复用计算单元（聚类、密度、几何/距离、稳健统计、谱分解、序列历史、变换、更新裁剪加噪、一小族文本函数），vocabulary 的 artifacts/coordinates/actions 也全是**联邦训练制品**（samples、gradients、local_update、uploads、aggregate、outgoing）和**联邦训练侧动作**（mask_samples…transform_broadcast）。而 Llama Guard 是**单模型、推理期**的输入输出安全分类器，paper 自己的 stage 就写着 `outside_training`：它的"防御计算"发生在一次前向里，不在联邦训练的任何一个制品上。

逐步看：

- **第 1、2 步（拼 prompt / 换 taxonomy）**：catalog 的 `text` 族只有 `split_words`（空白分词）、`hashed_bag_of_words`（词袋哈希）、`leave_one_out`（逐词删除）、`outlier_words`（ONION 的困惑度规则），**没有字符串模板渲染、拼接、槽位替换**。这也不是"普通张量运算"（compose 限定的是加减乘、比较、取索引、求均值），所以按严格口径它属于 **missing_op（text 族）**，而不是 compose。两步是同一个缺失单元的参数化（零样本只换槽位，少样本追加 2–4 条/类示例）。
- **第 3 步（前向 + 拿首位置 next-token 分布）**：模型句柄里 `model.generate(prompts)` 只回文本，`model.logprob(prompts, targets)` 只回**目标文本的平均对数概率**，`model.losses/hidden/activations/per_sample_gradients` 都不是词表分布——**没有任何方法暴露首个解码位置的概率/ logits**。vocabulary 的 `samples/text_logprob/word`（via model_handle）也只是"文本对数概率、可逐词删除比较"，粒度是词、读法是平均，不是首 token 分布。所以是 **needs_runtime**。
- **第 4 步（读 safe/unsafe 概率、二值化、1-vs-all）**：如果第 3 步能给出首位置 logits，这一步本来只是 softmax + 取两个词表下标 + 比较，属于 **compose**；但分布这个数据源运行时拿不到，也没有 tokenizer 去做 `'safe'/'unsafe' -> 单 token` 的映射，因此整体仍是 **needs_runtime**。catalog 的 `probe.fit_logistic/apply_logistic` 是在给定特征上训/用线性探针，**不能**读生成模型的首 token 概率，不能顶替。
  近似退路：对同一 prompt 分别以 target=`"safe"` / `"unsafe"` 调 `model.logprob` 比较两者。单 token 标签时它等于首 token 对数概率，但多 token 时得到的是几何均值，且论文本身不给阈值，所以只能算"能跑的近似 guard"，不是论文的读数。
- **第 5 步（输出裁决与类别清单）**：`unsafe\nO1` 这类字符串本质就是生成续写，`model.generate` 直接提供，属于 **runtime_data**；但运行时没有约束解码/合法标签集，续写是否符合"字母+1-based 序号"不受保证，且该步输入里的"首 token 判定"仍受第 3、4 步缺口拖累。序号转字母只是字符串拼接，不是可复用算子。
- **第 6 步（下游门控）**：论文明确"未定义、部署相关"，但它的性质是**推理时介入**（放行/拦截请求），运行时没有这种拦截钩子，vocabulary 里也没有任何对应动作，故按 **needs_runtime**（如果按"不属于论文方法"判，也可归 outside，这一点有歧义，见 note）。
- **另外**：论文真正的"训练一个指令微调的 guard 模型"这一步**不在流水线里**，它属于 outside（离线训练一个独立模型）；运行时也完全不做这件事。

**结论：partial。** 用现有东西可以拼出一个"近似的提示式安全分类器"——`model.logprob` 比两个标签 + `model.generate` 出文本；但严格意义的 Llama Guard（按 taxonomy 指南读首 token 概率并输出类别清单）表达不了，而且它根本不是一条联邦防御流水线，而是推理期外挂。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用的（别的方法也会用到，值得补进库/运行时）：**

1. **文本模板 / 角色标签 prompt 拼装**（`assemble_role_tagged_prompt`）：所有 prompt-based judge、guardrail、in-context 防御、系统提示与工具调用封装都要用。catalog 已有 `text` 族，说明文本算子在本库射程内，只是缺"拼装"这一支。
2. **首位置 next-token 概率 / 词表分布的句柄能力**：任何把 LLM 当分类器或打分器的检测方法都要用（logit-based 越狱检测、困惑度过滤、拒答概率、自评打分、生成式分类器）。现有 `model.logprob` 只覆盖"给定目标文本的平均对数概率"这一种读法，覆盖面明显偏窄，是运行时层面最有价值的通用补齐点。
3. **tokenizer / 标签到单 token 的映射 + 带标注的阈值校准（P-R/AUPRC 选阈值）**：所有把类别名当标签读概率的 guard 都需要。注意 catalog 的 `robust.quantile_threshold` 是"按良性样本分位点取上尾阈值"（无监督、给定 FPR），**不等于**"用带标注数据按 AUPRC/P-R 权衡选阈值"，两者不可互换，这也是一个通用缺口。
4. **小标签集上的约束解码**：让生成只落在 `safe/unsafe` + 类别集合内，是生成式分类器的通用需求（论文没提，属于实现细节）。

**这篇论文特有的（是内容/配置，不是可复用计算单元）：**

1. Llama Guard 的 **taxonomy 文本、指南措辞、四段式 prompt 版式（guidelines / type of classification / conversation / output format）与 4096 token 预算**——离线准备的内容与模板配置。
2. **"字母 + 1-based 序号"（O1…）的类别书写约定**和 **1-vs-all 逐类别重跑**——论文自己的输出约定与调用循环，不需要新算子。
3. **指令微调得到的 Llama2-7b guard 权重本身**——离线训练一个独立模型的产物。
4. **"不给阈值"**——这是方法留白，不是缺算子。

```json
{
  "key": "inan2023llamaguard",
  "steps": [
    {
      "n": 1,
      "class": "missing_op",
      "uses": [],
      "missing_name": "assemble_role_tagged_prompt",
      "missing_family": "text",
      "missing_io": "in: {guidelines: str（编号类别 + 安全/不安全的自然语言说明）, task_type: str（prompt 分类 / response 分类）, turns: list[(role, text)], output_format: str}；out: 带角色标签的 prompt 文本（受 4096 token 预算约束）",
      "note": "catalog 的 text 族（split_words / hashed_bag_of_words / leave_one_out / outlier_words）没有任何模板渲染、字符串拼接或槽位替换功能，严格按函数说明都不满足；这也不是加减乘/比较/取索引/求均值这类张量运算，故不能算 compose，只能新增一个通用的文本拼装单元。"
    },
    {
      "n": 2,
      "class": "missing_op",
      "uses": [],
      "missing_name": "assemble_role_tagged_prompt",
      "missing_family": "text",
      "missing_io": "in: 第 1 步 prompt 的可变槽位 + {category_names: list[str], descriptions: list[str] | None, few_shot: list[(category, input, output)]}；out: 替换/追加类别名与 2–4 条/类 in-context 示例后的 prompt",
      "note": "与第 1 步同一个缺失单元的参数化（零样本时只换槽位内容，少样本时在固定位置插入示例块），不需要第二个通用算子；catalog 里同样没有可用函数，不涉及张量运算。"
    },
    {
      "n": 3,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "缺的是运行时能力：没有句柄返回首个解码位置的 next-token 概率/词表分布（或指定标签串的单 token logit）。model.generate 只回文本；model.logprob 只回目标文本的平均对数概率；model.losses/hidden/activations/per_sample_gradients 都不是词表分布；vocabulary 的 samples/text_logprob/word 粒度是词、读法是平均，也不等价。同时缺 tokenizer/词表映射，无法把 'safe'/'unsafe' 定位到词表条目。疑点：单 token 标签时用 model.logprob 分别打分可近似首 token 对数概率，但多 token 时只是几何均值，也没有校准阈值，不算忠实实现。"
    },
    {
      "n": 4,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "这一步依赖第 3 步的首位置概率分布，而运行时拿不到该数据，也没有 safe/unsafe 的词表下标与阈值。若第 3 步缺口被补上（句柄返回首位置 logits），本步会退化为 compose：softmax + 两个下标索引 + 阈值比较，几行张量运算即可，catalog 无现成函数但也不需要新算子。catalog 的 probe.fit_logistic/apply_logistic 是在隐藏特征上训/用线性探针，与读生成模型首 token 概率是两件事，不能替代；1-vs-all 的逐类别重跑只是外层循环，不是新算子。"
    },
    {
      "n": 5,
      "class": "runtime_data",
      "uses": ["model.generate"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "'unsafe' + 换行 + 类别清单本身就是生成续写，模型句柄 model.generate(prompts) 直接提供。但运行时没有约束解码或合法标签集，续写是否严格符合 '字母+1-based 序号' 不受保证；类别序号转字母只是字符串拼接，不算可复用算子。该步输入中的'首 token 判定'部分仍受第 3、4 步缺口影响。"
    },
    {
      "n": 6,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "缺的是推理时介入的能力：运行时没有在服务路径上按判定结果放行/拦截输入输出的钩子，vocabulary 的 modified_by 全是联邦训练侧动作（mask_samples、edit_samples、transform_received、transform_gradients、transform_update、select_and_weight、replace_global、transform_broadcast），没有能承接 guard 判定的制品。歧义说明：论文明确说这一步未定义、是部署侧策略，若按'不属于论文方法本身'判也可归 outside；这里按'运行时做不了这个动作（要推理时介入）'归 needs_runtime。AUPRC 选阈值属部署调参，不是算子缺口。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "运行时没有任何句柄暴露首个输出位置的 next-token 概率或词表分布（model.generate 只给文本，model.logprob 只给目标文本的平均对数概率，其余句柄给损失/隐藏态/逐样本梯度），第 3、4 步的核心读数没有数据来源。",
    "算子库没有 prompt/指南模板拼装单元（text 族只有 split_words、hashed_bag_of_words、leave_one_out、outlier_words），运行时也没有 tokenizer 与 'safe'/'unsafe' 的单 token 词表映射，第 1、2 步无法落地。",
    "运行时没有推理时拦截/门控钩子，vocabulary 的 artifacts 与 modified_by 全是联邦训练侧对象与动作，guard 的判定无法接到任何制品上，因此整条流水线不是一条可执行的联邦防御流水线，而是推理期外挂。",
    "论文真正的 guard 模型训练（指令微调 Llama2-7b）不在流水线内，属离线训练一个独立模型（outside），运行时与算子库都不涉及。"
  ]
}
```
