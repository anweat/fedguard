# FreqFed: A Frequency Analysis-Based Approach for Mitigating Poisoning Attacks in Federated Learning

- Key：`fereidooni2024freqfed`；NDSS 2024；arXiv:2312.04432
- 作者：Hossein Fereidooni, Alessandro Pegoraro, Phillip Rieger, Alexandra Dmitrienko, Ahmad-Reza Sadeghi
- 类别：C3（服务器侧更新过滤，单轮横向）
- 阅读深度：摘要、威胁模型（§III）、设计（§IV）；实验表待补读

## 1. 威胁模型（§III, p.3）
- 目标：非定向（拒绝服务）或定向后门，同时维持主任务精度。
- 能力：完全控制 **k_A < K/2** 个客户端的数据、训练过程与超参；可修改上传权重；知道服务器聚合操作；可加正则项使 L2/余弦等度量低于阈值；可逐轮切换正常/恶意行为（间歇）；可做自适应攻击。
- 不假设 IID/non-IID。

## 2. 方法（§IV, pp.4–6）
1. 服务器对每个客户端上传的权重做 **2D DCT**。
2. **只保留低频系数**（从 DCT 矩阵左上角取子块）展平为向量——理由是权重的主要能量/信息集中在低频。
3. 以**余弦距离**对各客户端低频向量做 **HDBSCAN** 聚类，取最大簇。
4. 仅对最大簇内模型做 FedAvg。

## 3. 评测范围（摘要，p.1）
图像分类、**词预测（NLP）**、IoT 入侵检测、语音识别；声称对攻击类型与数据分布无关、效用损失可忽略（具体表待读）。

## 4. 与本项目的关系（我们的分析）
- **回答 ProtegoFed 的 DCT 疑问**：FreqFed 的增益来自“DCT + 低频截断”，截断改变了距离；完整正交 DCT 本身保距。ProtegoFed 在逐样本梯度上沿用 DCT 思路，需核对其是否同样截断。
- **多数假设**：取最大簇要求良性客户端占多数且在低频空间聚集；FedLLM-Attack/Safe-FedLLM 的每轮 3 客户端采样、30% 恶意比例下，单轮恶意占多数的情况会出现。自然 non-IID 下良性客户端也可能分裂成多簇。
- **与 ProtegoFed 组合（Table XII）**：样本级清洗 + FreqFed 更新过滤是现有文献中“客户端 + 服务器双端”的唯一定量组合证据，应列为双端体系的对照基线。
- **LoRA 迁移问题**：DCT 作用对象从 CNN 卷积核/全连接矩阵变为 LoRA A、B 或 ΔW=BA；A/B 分别做 DCT 受参数化非唯一性影响（BA=(BQ)(Q⁻¹A)），ΔW 做 DCT 更有意义但维度大（d×k）。
- 单轮横向方法，不利用历史；与 MCD/FLDetector 的纵向信号互补。

## 5. 待核对
- 低频子块大小如何选取；NLP 词预测实验的模型规模与攻击设置；non-IID 下 FPR。
