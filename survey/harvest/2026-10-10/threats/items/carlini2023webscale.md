## 1. 这篇论文的攻击做了什么

卡片描述的场景是 Web 规模训练数据集的**采集与分发供应链**：数据由维护者发布 URL 索引或周期性快照，客户端在训练前抓取。论文不涉及联邦学习、LoRA/PEFT、聚合服务器中的任何一项，攻击全部发生在**训练开始前的数据获取阶段**。攻击者是低资源外部攻击者：只能篡改索引中少量 URL 返回的**内容**，不能改 URL 列表、不能改标签或 caption，也不掌握维护者/curator 的内部细节。论文给出两条攻击：一是买下数据集里已过期的域名，使之后任何下载方抓到的都是攻击者内容（1000 美元预算内可控制每个数据集 0.02%–0.79%，最低约 60 美元控制 0.01%）；二是预测 Wikipedia 快照的抓取时刻并在抓取前一刻做恶意编辑，使恶意版本被固化进不可变快照（保守估计 6.5% 的文档可被投毒）。下游验证是在被投毒的 LAION-400M 上训 OpenCLIP：1000 张图（占 0.00025%）使指定图片零样本分类被翻转的成功率为 60%；10 张良性图配上被标为 UNSAFE 的 caption 后，使 NSFW 过滤器误判的成功率超过 90%。论文提出的防御只有数据层两种——完整性哈希与快照时间随机化，没有检测算法、没有剔除客户端/裁剪/加噪/修复等模型层动作。目标映射上，定向误分类落到词表的 `backdoor`，操纵 NSFW 安全过滤器落到 `safety_removal`（卡片自己把它记作 backdoor / jailbreak_safety）。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成两条：`data_source_content_substitution`（买过期域名、替换来源内容）与 `pre_snapshot_source_tampering`（抢在快照前篡改来源）。拆分的理由不是目标不同（两条目标相同，在词表里能力与制品也重合，都是 `local_data` → `samples`），而是**"靠什么拿到控制权"和"什么防御能拦住"完全不同**：前者靠对来源的持续控制，只有"可信参考摘要 + 训练前样本级校验"能拦下；后者靠对抓取时刻的预测，进入快照的内容本身就是哈希签发对象，只能靠调度层的时间随机化/延迟生效对付。若合成一条，入库时会把两个不同的拦截点混在一起，防御映射会失真。不拆第三条：定向误分类与 NSFW 过滤器误判是两条攻击共用的下游效果（同一类 payload），不是独立技术；论文也没有给出数据获取以外的第二条攻击路径。需要说明的是，词表能力枚举的粒度不足以表达"能预测快照时刻"，所以两条的 capabilities 都只能落在 `local_data`，它们的区别保存在 traces 与 stealth_measures 里。

## 3. 每个技术需要的能力与改动的制品

两条都写 `capabilities = [local_data]`、`modifies = [samples]`。论文里的攻击者其实是外部"数据提供方"（data provider）而不是某个联邦客户端，词表没有这个键，最贴近的是 `local_data`——被替换的内容最终就是"客户端拿到的本地样本"。两者都只改 `samples`：不改 gradients、trace、local_update、uploads、aggregate、outgoing、channel；不需要 aggregation、distribution、base_model、query_access、collusion、defense_knowledge。各自的额外前提卡片写得很清楚：第一条要求客户端不做完整性比对、且能持续控制 URL；第二条要求能预测抓取时刻并在检测窗口 ∆ 内完成编辑；两条共同的前提是不能改标签/caption、不能增删 URL。两条都是 `federated = false`：论文不是联邦设定。按"在联邦 LoRA 中最自然的对应"改写后，它们都变成"某客户端本地样本在其上游来源处被换成攻击者内容"：第一条对应较自然（客户端从外部语料/数据供应方取数时被替换）；第二条的时序前提（可预测且不可变的公开快照调度）在联邦 LoRA 中不存在（卡片第 9 节也是这么推断的），映射后只剩"在客户端把上游内容并入本地样本之前完成替换，使事后签发的参考摘要与投毒内容一致"这一残余形态。所以两条 `applicable` 都写 true（制品与能力能对上），但第二条的映射明显弱于论文原设定，实际使用时要重做威胁建模。

## 4. 可能留痕的位置与依据

第一条：样本内容与索引/标注时的内容不一致，最直接的痕迹在 `samples/manifest/sample`（论文用密码学哈希比较两次下载、检出内容已变，§4.4；完整性校验也以哈希不匹配为丢弃判据，§6.2）与 `samples/text/sample`（客户端抓到的就是攻击者返回的任意内容，§3.3、§4.1），这两条标 **reported**；再往训练里走，被替换的样本会产生与良性样本不同的逐样本梯度（`samples/gradient/sample`，论文只报告下游成功率、没做梯度测量），并最终在"加载客户端上传后探针"这一坐标上表现为目标行为（`uploads/probe_behavior/client`，论文是在集中式训练后的模型上验证的），这两条标 **inferred**。第二条：论文报告的痕迹是"快照临近时刻出现、随后被回退的编辑"，它落在 Wikipedia 的编辑历史里，迁移到联邦坐标只能落在按轮保留的数据版本特征上（`history/features/round`，inferred），加上快照文本本身含恶意版本（`samples/text/sample`，reported）；它的样本梯度痕迹同第一条（inferred），因为论文对这条攻击只估算了 6.5% 的可投毒比例、没有训练下游模型，所以没有写探针行为这一痕迹。特别注意 `samples/manifest/sample` **对第二条不成立**：哈希签发的对象就是已经含毒的快照，不会出现不匹配，这正是它需要调度层防御的原因。凡卡片只给了机制、没给测量的，我都标 inferred 并写清推断链，没有把集中式训练结果当成联邦里已测到的现象。

```json
{
  "key": "carlini2023webscale",
  "items": [
    {
      "technique_name": "data_source_content_substitution",
      "summary_zh": "控制数据集条目 URL 背后的内容来源（例如买下已过期的域名），使下载方抓到的样本与索引、标注时的内容不一致，从而把攻击者选定的内容当成客户端本地样本喂进训练。",
      "goal": ["backdoor", "safety_removal"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/manifest/sample", "basis": "reported", "note": "论文用密码学哈希把同一 URL 的内容与初始发布版本比对，检出内容已改变（§4.4）；完整性校验防御也以哈希不匹配作为丢弃判据（§6.2）。"},
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "客户端抓取时收到的是攻击者返回的任意内容，与维护者索引、标注时的内容不同（§3.3、§4.1）。"},
        {"coordinate": "samples/gradient/sample", "basis": "inferred", "note": "被替换的样本参与训练必然带进与良性样本不同的逐样本梯度；论文只报告了下游定向误分类成功率 60%（§4.5），没有做逐样本梯度测量。"},
        {"coordinate": "uploads/probe_behavior/client", "basis": "inferred", "note": "论文在集中式训练后的模型上验证了目标行为（零样本分类被翻转、NSFW 过滤器误判，§4.5）；迁移到联邦 LoRA 时，这一行为差异应随投毒客户端上传的适配器被加载后由探针检出。"}
      ],
      "variant_of": "",
      "stealth_measures": [
        "只替换 URL 返回的内容，不改索引里的 URL 列表与辅助标签/caption（§3.2），样本来源仍是原来那个域名，靠的是过期域名里的残余信任（§4.1）",
        "论文在局限里引用前人工作指出，即使改用感知哈希，攻击者也可以上传经过对抗修改的投毒图像来通过校验（§6.2）"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "pre_snapshot_source_tampering",
      "summary_zh": "先预测某条数据被抓取进不可变快照的时刻，再在该时刻之前的一小段时间里篡改上游内容，使恶意版本被固化进快照，事后的回退与审核都来不及把它移除。",
      "goal": ["backdoor", "safety_removal"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "快照中的文章文本包含随后被回退的恶意编辑（§5.1、§5.3），即本地样本内容与上游当前版本不一致。"},
        {"coordinate": "history/features/round", "basis": "inferred", "note": "论文的对应痕迹是“快照临近时刻出现、随后被回退的编辑”（§5.2.3、§5.3），它落在 Wikipedia 的编辑历史里；迁移到联邦 LoRA 只能体现为按轮保留的数据版本特征中出现一次短暂、随后消失的内容变化。"},
        {"coordinate": "samples/gradient/sample", "basis": "inferred", "note": "被固化进训练数据的恶意样本会带进与良性样本不同的逐样本梯度；论文对这条攻击只估算了可投毒文档比例 6.5%（§5.4），没有训练下游模型，也没有做梯度测量。"}
      ],
      "variant_of": "",
      "stealth_measures": [
        "恶意编辑抢在快照固化之前完成，回退发生在内容已经进入快照之后；快照不可变，人工审核无法把它拿掉（§5.1）",
        "论文把完整性哈希只列为 split-view 的防御（§6.2），抢跑要另靠调度层的时间防御（§6.3），即在哈希口径下含毒快照本身就是“正本”",
        "论文提到攻击者可调整编辑时刻 a 在“太早被回退”与“太晚错过快照”之间取舍（§5.4），并可转向不活跃文章或审核者更少的语种（§6.3）"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
