# carlini2023webscale：Poisoning Web-Scale Training Datasets is Practical

## 1. 基本信息

- **场景**：论文研究的既不是传统联邦学习（classic federated learning），也不是联邦大模型微调（federated LLM fine-tuning），也不是参数高效微调供应链（PEFT supply chain）。它研究的是**Web 规模训练数据集的采集与分发供应链**：数据集由维护者（maintainer）发布 URL 索引或周期性快照，客户端（client，即研究者或工程实践者）在训练前从互联网抓取或下载。论文全文没有出现联邦学习、LoRA、适配器（adapter）、参数高效微调、聚合服务器等概念中的任何一个作为研究对象。在下发枚举中只能归入 `other`。
- **训练阶段**：攻击发生在**训练开始之前的数据获取阶段**（数据集构建、索引发布、客户端抓取、快照生成）；论文中唯一涉及训练本身的部分是第 4.5 节与附录 B 的验证实验，即在被投毒的 LAION-400M 上训练一个 OpenCLIP 对比学习（contrastive learning）模型，用于确认投毒在下游模型上有效。
- **论文类型**：攻击（attack）为主，同时在第 6 节提出并部分落地了防御建议（完整性校验、时间随机化）。论文没有提出任何检测算法。
- **模型与数据规模**：攻击面测量覆盖正文所称的 10 个数据集，Table 1 实际列出 13 行，规模从 PubFig 的 0.06 百万条到 LAION-2B-en 的 2323 百万条，发布日期从 2010 年到 2023 年；Table 1 中标注“+”的 MMC4-FF、Falcon RefinedWeb、OBELISC 三行是论文首次发布之后新增的数据集。下游验证实验使用 OpenCLIP 的 ViT-B-32 架构，在 LAION-400M 上训练 32 个 epoch，批大小 3072，16 张 A100（§4.5、附录 B）。文本侧分析对象是英语 Wikipedia 快照与 Wiki-40B 多语言数据集（§5）。

## 2. 威胁模型

- **攻击者是谁**：论文假定存在“相对不熟练、低资源”（relatively unskilled, low-resource）的外部攻击者，他能够篡改少量 URL 的内容（§3.2，`Sadv ⊂ {urli}`）。论文明确说攻击者不是内部人员：“we assume the adversary has no specialized or insider knowledge about the curator, downloader, or maintainer”（§3.2）。在防护库的枚举里，他扮演的是“外部攻击者 + 篡改后的内容宿主（data provider）”这一角色——论文自己在描述分布式数据集时把 URL 背后的主机称为“data provider”（§4.1）。论文没有给出攻击者占参与方比例的数字，因为该场景不存在联邦参与方集合。
- **占比或数量**：论文未按“恶意客户端比例”陈述。可量化的规模是攻击者可控制的数据比例：在 1000 美元预算下每个数据集至少 0.02%–0.79%（§4.2），至少 0.01% 的 LAION-400M 或 COYO-700M 可用 60 美元控制（§1、§4.2）。
- **能力（能改什么）**：能篡改数据集索引中少量 URL 指向的**内容**。对分布式数据集，方式是购买过期域名从而在客户端抓取时返回任意内容（§4.1）；对集中式快照数据集，方式是在快照前短暂编辑内容（§5.1）。论文明确攻击者**不能**改辅助数据：`ci`（监督标签或文本描述）不受其控制，也不能向训练数据中增删任何 URL（§3.2）。
- **知识（知道什么）**：知道数据集索引中的 URL 集合 `{urli}`，因为这是维护者公开发布的；知道 Wikipedia 快照的公开调度信息与历史抓取速率（§5.2.2）。论文明确说他不知道 curator、downloader、maintainer 的内部细节（§3.2）。
- **目标**：论文实验验证了两种定向目标：(1) 让某张特定图片被 CLIP 零样本分类器误判为 ImageNet 的某个目标类别（§4.5、附录 B）；(2) 让 Stable Diffusion 1.4 的 NSFW 安全过滤器把一张良性图片判为 NSFW（§4.5、附录 B）。论文引用的更一般目标包括定向误分类与植入模型后门（§2）。论文没有研究无目标破坏与隐私窃取。
- **防御者是谁、能看到什么、信任什么**：防御者是维护者、curator 与下载器。论文第 6.1 节明确“all maintainers, curators, and downloaders are trusted and behave honestly”，维护者向所有客户端提供相同的索引，curator 决定每个条目进入快照的时间，下载器诚实地执行完整性校验。防御者能看到的量是：客户端下载到的内容、维护者发布的哈希、快照时间与编辑历史、以及可信版主的回退动作。防御者信任这些角色本身；**论文未说明**在维护者或 curator 被攻陷时如何防御，只在第 6.5 节把这类风险列为进一步工作。

## 3. 攻击入口与流程位置

攻击进入的位置是**本地数据准备（训练前的数据获取与数据集构建）**。它不进入本地训练过程、不进入更新上传前的后处理、不进入服务器聚合、不进入全局模型下发、也不进入评估与部署。具体步骤：

1. **Split-view poisoning（分裂视图投毒）** 的操作步骤（§4.1）：攻击者先统计数据集中哪些域名已经过期（DNS 记录不存在）且可购买，按“域名承载的图片数除以购买成本”排序，购买最划算的域名；此后任何客户端在抓取该 URL 时都会收到攻击者返回的任意内容。论文指出攻击者不需要知道客户端未来何时下载，因为拥有域名就保证未来所有下载都拿到投毒内容（§3.3）。论文报告的成本口径是 2023 年 Google Domains 报价（§4.2）。
2. **Frontrunning poisoning（抢跑投毒）** 的操作步骤（§5.1–§5.4）：攻击者先利用公开的快照进度统计与上一次快照的抓取速率，预测某篇 Wikipedia 文章被写入快照的具体时刻；再在该时刻之前做出恶意编辑（vandalism）；即使编辑随后被回退，恶意内容已经进入不可变的快照，从而永久留在训练数据里。攻击者通过调整编辑时刻 `t̂i + a` 在“编辑太早被回退”和“编辑太晚错过快照”两种失败模式之间取舍（§5.4）。

## 4. 方法原理

论文的方法包含两个攻击和两个防御，没有检测算法。

- **Split-view poisoning（§3.3、§4.1）**：核心思想是“维护者索引数据集时看到的内容”与“客户端训练时抓取到的内容”可以任意不同，因为索引里的 URL 内容是可变的，而数据集没有密码学完整性保护。攻击者购买过期域名即获得对该 URL 未来所有响应的持续控制权，论文称之为滥用过期域名中的“残余信任”（residual trust）。
- **Frontrunning poisoning（§5.1–§5.4）**：核心思想是 Wikipedia 派生数据集不是活数据而是快照，而快照过程是可预测的。论文给出的预测公式是：设当前与上一次快照的官方开始时间为 `t0` 与 `t0,prev`，文章 `i` 上一次被抓取的时间为 `ti,prev`，则本次抓取时间估计为 `ti ≈ t0 + (ti,prev − t0,prev)`（§5.2.2）。由于 Wikipedia 不公布每篇文章的实际抓取时间，论文用编辑历史反推：每篇文章的真实快照时间落在“最后一条被包含的编辑”和“第一条未被包含的编辑”之间，构成区间 `[tlow_i,prev, thigh_i,prev]`；再对同一抓取线程内的文章区间做线性拟合，得到 `t̂i,prev`，并保证区间上下界随文章序号单调递增（§5.2.3）。论文进一步用 `A(a)` 表示在时刻 `t̂i + a` 编辑时能进入快照的恶意编辑比例，其中同时乘上“被提前回退的概率 `prev(t̂i + a; thigh_i)`”与“编辑太晚的指示函数 `1[t̂i + a > tlow_i]`”，对 `a` 扫描取最大得到 `max_a A(a) = 0.065`，即保守估计可投毒 6.5% 的 Wikipedia 文档（§5.4）。
- **防御一：完整性校验（§6.2）**：维护者或可信第三方在时间 `ti` 为原始内容 `xi` 附带密码学哈希 `hi = H(xi)`，下载器校验 `H(x′i) = hi`，其中 `x′i` 是 `t′i` 时刻 URL 的内容，不匹配的数据被丢弃；论文建议 `H` 使用 SHA-256 之类的密码学哈希函数。
- **防御二：时间型防御（§6.3）**：核心是拉长攻击者必须保持控制权的时间 `d = ti − t̂i`，使其超过 curator 检测恶意修改所需的时间 `∆`，从而让 `d > ∆`。两种实现是：随机化快照顺序并延长整个语料的快照时长；或者先冻结内容、等待 `T > ∆` 让编辑经过审核，再在 `ti + T` 发布快照并回填可信版主的修改或回退。论文给出的保护比例公式是 `1 − ∆/(tn − t0)`，在英语 Wikipedia `∆ = 2.5` 小时、快照在 24 小时内均匀随机化时保护 89.5% 的文章（§6.3）。
- **第 6.4 节的通用防御方向**：对 Common Crawl 这类没有“黄金快照”也没有可信 curator 的数据集，论文提出基于共识（consensus）的思路，即只有当某个图文对出现在许多不同网站上时才信任它；论文明确把具体方案留给未来工作。

## 5. 检测或防御所需的数据

（论文是攻击论文，因此下面同时列出“防御方法需要的输入”与“攻击留下的可观测量/论文声称能绕过的检测”。防护库的钩子枚举是联邦学习式的，本论文不存在对应的客户端与服务器钩子，映射位置仅供对照。）

**防御方法需要的输入：**

1. **原始内容的密码学哈希 `hi = H(xi)`**。是什么：维护者在内容尚未被攻击时对原始字节计算的哈希，论文建议 SHA-256。在哪里采集：维护者侧在索引/快照生成时计算，客户端在训练前下载数据集时用于比对（对应枚举 `client_pre_train`）。粒度：逐样本。是否需要跨轮历史：不需要。是否需要干净参考数据：需要，`hi` 本身就是可信参考值。是否需要额外前向或反向计算：不需要（哈希计算，论文未报告具体开销）。
2. **客户端实际抓取到的内容 `x′i`**。是什么：URL 在下载时刻返回的原始字节（图像或文本）。在哪里采集：客户端训练前的数据抓取环节（`client_pre_train`）。粒度：逐样本。是否需要跨轮历史：不需要。干净参考数据：需要与 `hi` 配对。额外计算：需要对每个样本计算一次哈希。
3. **数据集索引元组 `{(urli, ci)}`**。是什么：URL 与固定的辅助数据（标签或自动抽取的 caption）。在哪里采集：随数据集一起下载（`client_pre_train`）。粒度：逐样本。跨轮历史：不需要，但如果要检测“索引本身被篡改”则需要（论文第 6.5 节提到维护者可能被攻陷）。额外计算：不需要。
4. **内容变化检测用的感知哈希（perceptual hash）或嵌入**。是什么：论文提到 COYO-700M 用 pHash 校验良性图像变化，作者自己在第 4.4 节用 CLIP 余弦相似度（阈值 < 0.99）与密码学哈希来寻找“内容已变且域名所有权已变”的攻击签名。在哪里采集：数据集版本比较或审计时（`evaluation`）。粒度：逐样本。跨轮历史：需要（要与初始发布版本比较）。干净参考数据：需要。额外计算：需要（CLIP 前向或 pHash 计算）。
5. **域名状态与所有权信息**。是什么：DNS 查询结果（NXDOMAIN 表示过期）、注册商是否挂牌出售、WHOIS 的最近购买日期。在哪里采集：抓取前或审计时（`client_pre_train` / `evaluation`）。粒度：按域名（论文按承载图片数聚合到域名级，再折算回样本比例）。跨轮历史：需要（第 4.4 节靠“域名所有权是否变化”区分攻击与正常的重新编码）。干净参考数据：不需要。额外计算：不需要，但需要外部 DNS/WHOIS 查询。
6. **Wikipedia 编辑历史与快照调度信息**。是什么：每次编辑的时间与编辑注释、哪些编辑进入了快照、哪些被回退，以及 Wikimedia 公开的 dump 开始时间与实时进度统计。在哪里采集：curator 侧与审计侧（`evaluation` / 服务器侧）。粒度：逐编辑、逐文章，快照调度是逐轮（每个 dump）。跨轮历史：需要（预测公式依赖上一次快照的 `ti,prev` 与 `t0,prev`）。干净参考数据：不需要。额外计算：不需要。
7. **可信版主的回退（reversion）动作**。是什么：可检测到恶意修改的编辑或管理员操作，论文的第二种时间防御靠它回填快照。在哪里采集：curator 侧的审核流程（`evaluation`）。粒度：逐编辑。跨轮历史：需要（时间窗口 `T` 内的回退）。额外计算：不需要。
8. **下载访问日志**。是什么：作者在购买域名后记录的时间、IP 哈希、完整 URL 与请求头，用于测量数据集仍被下载的频率。在哪里采集：作者自建服务器侧（这不是防御方法本身需要的输入，而是论文用来量化影响的测量数据）；在枚举中归入 `evaluation`。粒度：逐请求/逐样本。跨轮历史：需要（12 个月的持续记录）。额外计算：不需要。
9. **模型行为验证数据**。是什么：目标图片在零样本 CLIP 分类下的输出、或 NSFW 过滤器的判定结果。在哪里采集：评估时（`evaluation`）。粒度：逐样本（每张目标图片）。额外计算：需要一次前向。

**攻击留下的痕迹与论文声称能绕过的检测：**

- 痕迹包括：域名从可解析变为 NXDOMAIN 或所有权/最近购买日期变化；同一 URL 的内容与初始发布版本的密码学哈希或感知哈希不一致（§4.4）；Wikipedia 文章在快照临近时刻出现随后被回退的编辑（§5.2.3、§5.3）。
- 论文声称能绕过：在论文写作时 Table 1 所列 13 个数据集中绝大多数没有密码学哈希（只有 FaceScrub 与 PubFig 有，且它们的第三方下载器几乎都不校验，§6.2）；感知哈希不抗对抗样本，论文引用前人工作说明攻击者可以上传经过对抗修改、仍通过感知哈希的投毒图像（§6.2 局限）；人工审核无法阻止抢跑投毒，因为快照不可变，回退发生在内容已经进入快照之后（§5.1）。

## 6. 干预动作

论文提出的动作全部是**数据层动作**，不是模型层动作：

1. **完整性校验（§6.2）**：下载器丢弃哈希不匹配的样本，即样本级过滤（filter samples）。动作发生在客户端训练之前的数据准备环节，也就是论文所说的“downloader”环节。论文报告，在其负责任披露之后，CC3M、CC12M、LAION-2B-en、LAION-2b-multi、LAION-1B-nolang 与 LAION-400M 已在数据集中发布图像内容的 SHA-256 哈希，并且 `img2dataset` 增加了下载时校验 SHA-256 的选项（§6.2）；全文在第 1 节说明共有 6 个数据集采纳了推荐实现。
2. **随机化快照顺序（§6.3）**：curator 改变内容进入快照的顺序，并要求攻击者控制内容长达整个快照时长 `tn − t0`。动作发生在 curator 侧（对应服务器/分发侧），不涉及客户端。
3. **时间门控与可信回填（§6.3）**：curator 先抓取并冻结内容，等待 `T > ∆`，再把可信版主在这段时间内的修改或回退回填进最终快照；论文强调后续编辑只能来自可信版主，以避免攻击者选择性删除。动作同样发生在 curator 侧。
4. **论文没有提出的动作**：剔除客户端、重新加权、梯度裁剪、加噪、模型修复、模型回滚。这些在论文中均未出现。

## 7. 实验设置与主要结果

- **数据集与规模**：Table 1 列出 13 个数据集（正文口径为 10 个），规模 0.06M–2323M，发布时间 2010–2023。所有数据集在 2023 年都有超过 0.01% 的数据可被购买（Table 1 表头）。
- **过期域名测量口径（§4.2）**：对每个域名在两个地理位置不同的数据中心、于 2022 年 5 月与 2022 年 8 月共做四次 `nslookup`，四次全部返回 NXDOMAIN 才算过期；再要求 2022 年 8 月至少一家注册商将其列为待售才算可购买；按“域名承载图片数 / 购买成本”降序累加，报告 1000 美元预算内可购买的比例。结果：每个数据集至少 0.02%–0.79% 的图片可被控制（§4.2）；Figure 1 显示至少 0.01% 的数据可用不到 60 美元控制（§4.2）。COYO-700M 在 2022 年 8 月 30 日发布当天就有 0.1% 的图片位于 1000 美元以内可购买的过期域名上（§4.2）。
- **下载率测量（§4.3）**：每个数据集购买 3 个最热门的可购买过期域名与 3 个随机域名（共 6 个），从 2022 年 8 月起运行服务器 12 个月；服务器每月收到约 1500 万次请求，约每秒 6 次。判定标准是 recall（某 IP 在时间窗内下载了受控 URL 的至少 90%，且覆盖全部 6 个域名）与 precision（该 IP 在时间窗内对受控域名的请求中至少 50% 指向数据集内的 URL）。CC-3M 的例子：每月 51,000 次图片请求来自 2401 个唯一 IP；只加 precision 约束降到 2007 个 IP 与 43,000 次请求，只加 recall 约束降到 70 个 IP 与 32,000 次请求，两者同时施加后为 64 个 IP 与 28,000 次请求（§4.3）。Table 1 最后一列显示，即使最老、访问最少的数据集也仍有每月至少 3 次下载；论文同时写到“over the six months we tracked data, there were over 800 downloads that we could have poisoned”（§4.3）。
- **在野利用检查（§4.4）**：在 CC3M 上，用感知相似度只找到 1 个符合攻击签名的域名（实为域名囤积者投放广告），用密码学哈希多找到 2 个已被重新购买的域名（但所有权未变，只是 DNS 记录短暂失效并重新编码）；在 LAION-400M 上，用 CLIP 余弦相似度 < 0.99 比较，在第一次与第二次下载时分别有 5.6M 个域名中的 4.1M 与 4.2M 个域名承载至少一张被修改的图片，共 175M 与 183M 张被修改图片，但抽样检查未发现恶意域名。
- **下游投毒效果（§4.5、附录 B）**：在 LAION-400M 上训练 OpenCLIP ViT-B-32，32 个 epoch，批大小 3072，16 张 A100。目标误分类实验：选 10 个 ImageNet 类，每类选 1000 个 caption-image 对，把图片替换为同一张无关图片，即每个类投毒 1000 张；正文写“0.00025% of the total dataset”，附录 B 写“0.000025% of the data”（两处数值不一致，照原文分别记录），成功率为 60%（§4.5）。NSFW 实验：选 10 张良性图片，各配 1000 个在 LAION-400M 元数据中标注为 UNSAFE 的 caption，把对应图片替换为该良性图片，成功率高于 90%（§4.5）。
- **Wikipedia 预测精度（§5.2.4、§5.3）**：对上一次快照时间的线性拟合，与未知真值的最大绝对误差平均为 27 分钟（Figure 4）；对下一次快照时间的预测在多数情况下误差在 30 分钟以内（Figure 5），且误差偏向负值（预测偏早，因为快照过程会略微加速）。回退时间分布见 Figure 6，约 35% 的回退超过 30 分钟（Figure 6 说明文字）；正文写“Approximately 32% of reversions take more than an to be reverted”，该句在抽取文本中缺失时间单位，但从上下文（结合约一小时的总不确定度）看指的是一小时。综合后保守估计 `max_a A(a) = 0.065`，即可投毒 6.5% 的 Wikipedia 文档（§5.4）。
- **多语言 Wikipedia（§5.5）**：在 Wiki-40B 的 39 种非英语语言中对 35 种重复了分析（Figure 7 的说明文字写 36 种），发现 22 种（63%）比英语 Wikipedia 更容易投毒；可行的投毒率从 0.95% 到 25.3%，中位数 8.2%（§5.5）。
- **防御效果（§6.2、§6.3）**：防御的可用性代价方面，2018 年下载的 CC-3M 原始 330 万张图片中仍有 290 万张在线，但只有 110 万张的哈希与原始一致，另外 180 万张已经变化（§6.2）；附录 E 写“adding hashes to CC-3M reduces its size by a factor of three”。时间防御方面，英语 Wikipedia 的 `∆` 为 2.5 小时，24 小时内均匀随机化快照可保护 89.5% 的文章；把回退窗口从 5 分钟增加到 1 天，可把回退率从 50% 提高到 90%，把 vandalism 减少 5 倍（§6.3）。
- **指标口径**：论文没有联邦学习意义上的客户端数、参与率、轮次、恶意客户端比例、非独立同分布（non-IID）设置等实验；这些都**论文未说明**。论文使用的指标是“可购买数据比例”“每月下载次数”“投毒成功率”“预测误差（分钟）”“回退时间 CDF”“可投毒文档比例”。

## 8. 开销

- **攻击的金钱开销**：论文报告 0.01% 的 LAION-400M 或 COYO-700M 可用 60 美元投毒（§1）；Table 1 与 §4.2 按 1000 美元预算统一计算；“至少 0.01% 的每个数据集可以用不到 60 美元每年控制”（§4.2）；Figure 1 给出“可控制图片比例—成本”曲线，成本按 2023 年 7 月 Google Domains 报价测量。
- **作者的测量基础设施开销**：每个数据集购买 6 个域名，从 2022 年 8 月起运行日志服务器 12 个月，每月约 1500 万次请求（§4.3）。这些是研究测量的开销，不是防御开销。
- **防御的可用性与存储代价**：论文称两个防御是“低开销”（low-overhead，§1），但**没有报告**计算或通信开销的具体数值。可量化的代价是完整性校验带来的数据可用性损失：CC-3M 的 330 万张原图中只有 110 万张哈希仍然匹配（§6.2），附录 E 说为 CC-3M 加哈希会让数据集缩小到三分之一。哈希本身的存储开销**论文未报告**。
- **论文未报告**：任何联邦学习意义上的计算、通信或存储开销（因为论文不做联邦学习）。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文自述）：**

1. 对分布式数据集，客户端不会把下载到的本地副本 `D′` 与维护者索引的原始数据 `D` 做密码学完整性比对；对集中式数据集，curator 检测任意 URL 内容被恶意修改需要至少时间 `∆`，因此攻击者在 `ti − ∆ ≤ tˆi ≤ ti` 区间内的投毒不会被发现（§3.2）。
2. 攻击者能持续控制部分 URL（split-view）或能精确预测内容被抓取的时间（frontrunning）（§3.3、§5.1）。
3. 维护者、curator 与下载器全部诚实，不协助攻击者（§3.2）；防御章节进一步要求维护者向所有客户端分发相同索引、下载器诚实执行校验、curator 控制快照时间（§6.1）。
4. 攻击者不能修改辅助数据 `ci`，也不能增删 URL（§3.2）。
5. 时间防御假设攻击者无法用 Sybil 账号在首次检测与回退之后自动重新引入恶意编辑，论文明确说“If this assumption is invalid, this protection will be weaker in practice”（§6.3）。

**论文自述的局限：**

- 完整性校验只有在良性内容保持静态时才可用；任何重新编码、裁剪、缩放或上传更高分辨率图片都会导致哈希不匹配，从而损害数据效用（§6.2）。改用感知哈希可以提高效用，但不能有意义地阻止投毒，因为攻击者可以上传经过对抗修改、能骗过感知哈希的图片（§6.2）。
- 时间防御只是让抢跑更难，不能完全阻止，因为 `∆` 在不同文章之间不均匀，攻击者可以转向不活跃的文章或审核者更少的语言（§6.3）；这两种防御还依赖于存在能够检测恶意编辑的可信 curator（§6.3）。
- 对 Common Crawl 这类通用 Web 数据集，既没有可信的“黄金快照”，也没有可信 curator，页面版本之间的差异也没有可用的信任信号，论文认为任何域名信任判断都是临时的（ad-hoc）（§6.4）。
- 论文第 6.5 节指出整个生态依赖隐式信任：客户端信任维护者分发相同的辅助数据、信任 curator 做有效审核、信任下载器准确抓取、信任网站每次都返回同样的内容。

**自适应攻击者：**论文**没有**做自适应攻击者的实验评估。它只在讨论中提到两类自适应可能：攻击者用 Sybil 账号反复重放恶意编辑（§6.3），以及用对抗样本绕过感知哈希（§6.2，引用文献 [35]、[41]、[95]）。因此本项记为未评估。

**分析：迁移到联邦大模型 LoRA 微调时可能失效的假设**

- 分析：论文的攻击入口是“公开可下载的数据集内容”，而联邦 LoRA 微调中每个客户端的训练数据是本地私有、既不上传也不下载的。购买过期域名或抢跑快照都无法影响其他客户端的本地样本，因此 split-view 与 frontrunning 这两个具体攻击在联邦 LoRA 场景中**没有直接对应物**。
- 分析：完整性校验要求存在一个可信的参考哈希 `hi = H(xi)`，其来源是维护者手里的原始内容。在联邦 LoRA 中服务器通常不持有客户端的原始样本，无法为每个样本签发参考哈希；若改为服务器下发一份可信参考语料，就与“数据不出本地”的隐私目标冲突，并且会重新引入对服务器诚实性的信任依赖——而论文第 6.1 节的信任假设恰好与“服务器可能恶意”的联邦威胁模型方向相反。
- 分析：论文的检测与干预是逐样本内容级的（比较字节或感知哈希、丢弃不匹配样本）。联邦 LoRA 中服务器能看到的通常只是客户端上传的 LoRA 增量（逐层低秩矩阵）、更新范数、以及可选的训练元数据，看不到样本；论文的防御机制无法直接在服务器钩子上复现。
- 分析：论文的危害阈值（0.01% 数据即可投毒，1,000 张图即可达到 60%/90% 成功率）是在对比学习与 4 亿量级图文预训练上测得的。LoRA 微调的样本量、可训练参数量、更新范数分布与优化轨迹都不同，这些数字不能直接搬到联邦 LoRA 上当作阈值。
- 分析：论文的快照调度假设在联邦训练中不存在对应结构——联邦的样本选择是随机的、按轮次进行的，攻击者难以像预测 Wikipedia dump 那样预测某个本地样本何时被使用。论文未说明这一点，属于我的推断。
- 分析：论文完全没有涉及 LoRA、适配器合并、参数高效微调的更新结构、拜占庭鲁棒聚合（Byzantine-robust aggregation）或安全聚合（secure aggregation），所以在迁移时必须重新做威胁建模；论文对“联邦”二字没有任何陈述。

## 10. 对防护库设计的含义

- 分析：这篇论文的方法完全落在“训练前的数据获取”这一信任边界上，因此防护库的采集底座必须支持**数据条目级**的采集点（条目标识、来源、内容摘要、采集时刻），而不只是梯度、更新或激活。如果把采集点只定义在客户端训练中与服务器聚合时，这篇论文的攻击与防御都无法被表达。
- 分析：防御需要两类可配对的视图：“待检内容”（客户端或下载器实际拿到的字节）与“可信参考摘要”（由维护者或可信第三方签发的哈希）。因此库需要区分“参考数据”与“待检数据”，并允许参考值来自训练参与者之外的第三方；论文特有的是“参考值来自可信维护者”这一信任根，通用的部分是“参考值与内容分离存储、可插件化校验”。
- 分析：干预接口应包含**样本/条目级的过滤动作**，并且必须在训练开始之前生效，而不是聚合时的客户端剔除（exclude client）。论文的动作是“丢弃哈希不匹配的样本”，没有重新加权、裁剪、加噪、模型修复或回滚，因此库的干预接口应把“数据层动作”和“模型层动作”分开建模。
- 分析：时间型防御需要的是**调度器级别的接口**：随机化数据进入快照或被采样的顺序、延迟数据生效并回填可信修改。这类动作既不是客户端钩子也不是服务器钩子能表达的；库如果只有“客户端钩子 + 服务器钩子”，应至少提供“数据调度/版本发布”这一类钩子，否则论文第 6.3 节的防御无法插件化。
- 分析：跨轮历史是这篇论文的核心依赖之一（预测公式需要上一次快照的时间，在野检测需要与初始发布版本比较），因此库的存储层应支持“按数据条目保留跨版本历史”，这与联邦学习中“按客户端保留跨轮更新历史”的需求形态一致，可以复用同一套历史视图抽象。
- 分析：通用的需求是“训练前采集点 + 可插拔样本过滤钩子 + 跨版本元数据存储 + 参考值管理”；本论文特有的需求是“URL/快照式数据源模型”和“可信第三方签发内容摘要”，这两项在联邦 LoRA 中必须重新设计，不能照搬。

## 11. 原文依据

1. **§1 Abstract** — 支撑第 1 节与第 3 节关于论文类型与攻击实用性的论断。
   > "In this paper, we introduce two new dataset poisoning attacks that intentionally introduce malicious examples to a model’s performance. Our attacks are immediately practical and could, today, poison 10 popular datasets."
2. **§3.2 Threat Model** — 支撑第 2 节关于攻击者身份、能力与低资源特征的论断。
   > "We assume the existence of a relatively unskilled, low-resource adversary who can tamper with the contents of a small number of URLs"
3. **§3.2 Threat Model** — 支撑第 2 节关于攻击者知识与能力边界（不能改标签、不能增删 URL）的论断。
   > "the adversary has no control over the auxiliary data ci (e.g., supervised labels or text descriptions), nor can they add or remove any URLs from the training data that will be crawled by a client or curator."
4. **§3.2 Threat Model** — 支撑第 2 节与第 9 节关于防御者信任假设的论断。
   > "We further assume all maintainers, curators and downloaders behave honestly and do not assist the adversary in any way."
5. **§4.1 Our Attack: Purchasing Expired Domains** — 支撑第 3 节与第 4 节关于 split-view 投毒入口与“残余信任”原理的论断。
   > "Split-view poisoning abuses the residual trust inherent in an expired domain, as in traditional domain hijacking attacks"
6. **§5.1 Our Attack: Editing Wikipedia** — 支撑第 3 节与第 4 节关于 frontrunning 攻击入口与预测快照时刻的论断。
   > "This makes it possible to mount what we call a frontrunning attack. An attacker who can predict when a Wikipedia page will be scraped for inclusion in the snapshot can perform poisoning immediately prior to scraping."
7. **§1 Contributions / Defenses** — 支撑第 5 节与第 6 节关于完整性校验这一防御的输入与动作的论断。
   > "Integrity verification prevents split-view poisoning by distributing cryptographic hashes for all content, thus ensuring that clients observe the same data as when maintainers first indexed and annotated it."
8. **§6.3 Preventing Frontrunning Poisoning** — 支撑第 6 节关于时间型防御的干预动作与发生位置的论断。
   > "This can be achieved in one of two ways: (1) curators can randomize the snapshot order of the urli and extend the time required to snapshot the complete corpus"
9. **§6.2 Preventing Split-View Poisoning（Limitations）** — 支撑第 9 节关于感知哈希可被自适应攻击者绕过、防御存在可用性代价的论断。
   > "Switching to a perceptual hash function (which aims for invariance to small image changes) would lead to higher utility, but would not meaningfully prevent our poisoning attacks"
10. **§4.5 Putting It All Together** — 支撑第 7 节关于下游投毒实验设置与 60% 成功率的论断。
    > "When we poison 1,000 images (0.00025% of the total dataset) our attack has a success rate of 60% in flipping the model’s zero-shot classification of the targeted image."

```json
{
  "key": "carlini2023webscale",
  "title": "Poisoning Web-Scale Training Datasets is Practical",
  "year": 2023,
  "paper_type": "attack",
  "setting": "other",
  "uses_lora_or_peft": false,
  "adversary": ["external", "data_provider"],
  "attack_goal": ["backdoor", "jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "客户端抓取 URL 时实际收到的原始内容字节（图像/文本），即 x′i", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "维护者签发的原始内容密码学哈希 hi = H(xi)（建议 SHA-256）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "数据集索引元组 (urli, ci)，即 URL 与固定的标签或 caption", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "感知哈希（如 COYO-700M 的 pHash）或 CLIP 嵌入，用于跨版本检测内容变化", "where": "evaluation", "granularity": "sample", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "域名状态与所有权：DNS 解析结果（NXDOMAIN 表示过期）、注册商挂牌信息、WHOIS 最近购买日期", "where": "client_pre_train", "granularity": "sample", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "Wikipedia 编辑历史（编辑时间、编辑注释、是否被回退）与公开的快照开始时间及抓取速率统计", "where": "evaluation", "granularity": "sample", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "可信版主的回退或修改动作，用于在冻结窗口 T 内回填快照", "where": "evaluation", "granularity": "sample", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "作者自建服务器的下载访问日志（时间、IP 哈希、完整 URL、请求头），用于测量数据集下载率", "where": "evaluation", "granularity": "sample", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "目标图片的模型输出：零样本 CLIP 分类结果或 NSFW 安全过滤器判定", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["both"],
  "assumptions": [
    "分布式数据集的客户端不会把下载到的本地副本与维护者索引的原始数据做密码学完整性比对",
    "集中式数据集的 curator 检测任意 URL 内容被恶意修改至少需要时间 ∆，因此 ti − ∆ ≤ tˆi ≤ ti 内的投毒不会被发现",
    "攻击者能持续控制部分 URL（split-view）或能精确预测内容被抓取的时刻（frontrunning）",
    "维护者、curator 与下载器全部诚实且不协助攻击者，维护者向所有客户端分发相同索引，下载器诚实执行校验",
    "攻击者不能修改辅助数据 ci（标签或文本描述），也不能增删数据集中的 URL",
    "时间型防御假设攻击者无法用 Sybil 账号在首次检测与回退后自动重新引入恶意编辑",
    "完整性校验假设良性内容保持静态，任何重新编码、裁剪或缩放都会导致哈希不匹配"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract / §1", "supports": "第 1 节与第 3 节：论文类型为攻击，且攻击对象是 Web 规模训练数据集", "text": "In this paper, we introduce two new dataset poisoning attacks that intentionally introduce malicious examples to a model’s performance. Our attacks are immediately practical and could, today, poison 10 popular datasets."},
    {"section": "§3.2 Threat Model", "supports": "第 2 节：攻击者是低资源外部攻击者，只能篡改少量 URL 的内容", "text": "We assume the existence of a relatively unskilled, low-resource adversary who can tamper with the contents of a small number of URLs"},
    {"section": "§3.2 Threat Model", "supports": "第 2 节与第 9 节：攻击者不能修改标签等辅助数据，也不能增删 URL", "text": "the adversary has no control over the auxiliary data ci (e.g., supervised labels or text descriptions), nor can they add or remove any URLs from the training data that will be crawled by a client or curator."},
    {"section": "§3.2 Threat Model", "supports": "第 2 节与第 9 节：防御者信任维护者、curator 与下载器全部诚实", "text": "We further assume all maintainers, curators and downloaders behave honestly and do not assist the adversary in any way."},
    {"section": "§4.1 Our Attack: Purchasing Expired Domains", "supports": "第 3 节与第 4 节：split-view 投毒从训练前数据获取环节进入，原理是滥用过期域名的残余信任", "text": "Split-view poisoning abuses the residual trust inherent in an expired domain, as in traditional domain hijacking attacks"},
    {"section": "§5.1 Our Attack: Editing Wikipedia", "supports": "第 3 节与第 4 节：frontrunning 投毒依赖对快照抓取时刻的精确预测，入口仍是训练前数据准备", "text": "This makes it possible to mount what we call a frontrunning attack. An attacker who can predict when a Wikipedia page will be scraped for inclusion in the snapshot can perform poisoning immediately prior to scraping."},
    {"section": "§1 Contributions / Defenses", "supports": "第 5 节与第 6 节：完整性校验需要维护者签发的哈希作为可信参考，动作是丢弃不一致的数据", "text": "Integrity verification prevents split-view poisoning by distributing cryptographic hashes for all content, thus ensuring that clients observe the same data as when maintainers first indexed and annotated it."},
    {"section": "§6.3 Preventing Frontrunning Poisoning", "supports": "第 6 节：时间型防御通过随机化快照顺序与延时来干预，发生在 curator 侧", "text": "This can be achieved in one of two ways: (1) curators can randomize the snapshot order of the urli and extend the time required to snapshot the complete corpus"},
    {"section": "§6.2 Preventing Split-View Poisoning (Limitations)", "supports": "第 9 节：感知哈希可被自适应攻击者绕过，完整性校验存在局限", "text": "Switching to a perceptual hash function (which aims for invariance to small image changes) would lead to higher utility, but would not meaningfully prevent our poisoning attacks"},
    {"section": "§4.5 Putting It All Together", "supports": "第 7 节：下游 OpenCLIP 实验中投毒 1000 张图片即达到 60% 的目标误分类成功率", "text": "When we poison 1,000 images (0.00025% of the total dataset) our attack has a success rate of 60% in flipping the model’s zero-shot classification of the targeted image."}
  ]
}
```
