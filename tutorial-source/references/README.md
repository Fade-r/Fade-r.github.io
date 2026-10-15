# External references and provenance

_第三方代码、官方资料、许可和版本锁定索引；核验日期 2026-07-11_

2026-10-15 补充：[TI 官方资料核验记录](verification/ti.md)包含 IWR1443 / IWR1843 的 LVDS 差异和 xWR14xx I/Q 格式核验；[PySDR 写法参考](verification/tutorial-style.md)记录教学页面来源。旧版指纹记录保留，新下载版本不覆盖旧结论。公开分支仅保存这些记录，不附带第三方下载缓存。

---

## 📚 PKU tutorial upstream

本地 MATLAB 三件套属于 StZhang-B 的 PKU Millimeter Wave Radar Tutorial 代码族，但该目录是“教程派生的本地种子集合”，不是完整、未改写的上游 checkout。canonical repository、固定提交和许可证分别见参考项。[^1][^2][^3]

| Local file | Provenance evidence |
| --- | --- |
| `pku-mmwave-tutorial/DCA1000_Read_Data.m` | 与上游逐字节一致；SHA-256 `EBD4F660D5825FE0B99D98E2D920486D83AD22D25463A3BB6E7DE0C4DD5BEE14` |
| `pku-mmwave-tutorial/generateParameter.m` | 与上游逐字节一致；SHA-256 `F4D7B5D8DBB87295C6CE6EA961AB89FE57F1B0F282B55FCE1501A133AF731D38` |
| `pku-mmwave-tutorial/demo.m` | 既有本地种子：69 行中 66 行与上游一致；本地 SHA-256 `65FE9EDE0DCB2671A44B8C3DA7797D6F6422B10716050CB20893FD9968FAF237`；固定提交上游 SHA-256 `4D2BF3470AB2D5DDCFFE119362650171A53EF6344B5F7303AC09E3738F22B436` |

`demo.m` 的三处既有差异是第 4、11 行增加 MATLAB lint 注释 `%#ok<GVMIS>`，以及第 15 行把上游绝对采集路径的 `C:` 盘改成 `D:` 盘。它被保留用于复现本项目形成过程，不应被误称为未改写的 provenance 基线。

许可证原文保存在 [`licenses/PKU-Millimeter-Wave-Radar-Tutorial-MIT.txt`](./licenses/PKU-Millimeter-Wave-Radar-Tutorial-MIT.txt)。

## 📡 TI official documents

项目默认只保留链接和版本锁，不提交 PDF 二进制。五份资料当前均已核验为公开 PDF。[^4][^5][^6][^7][^8]

| ID | Purpose | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| IWR1443 datasheet (SWRS211T；symlink URL 可变) | 芯片能力、天线和接口 | 2,249,646 | `B354BC5932779CD44AD42CB95E251C85D87E06D1106C0BC9B1BA8A3455F6776D` |
| SPRUIJ4A | DCA1000EVM 使用说明 | 4,121,338 | `43E0DAEF8D6360EB20893D39CB9CBD464796F1D78608B7F203742FD2CE6B4023` |
| SWRA581B | ADC raw capture 格式 | 1,659,940 | `4A7D7E6D20E3D2A567D330B871D434259EACCAB605D9CE264EE504FA74A65EE0` |
| SWRA553A | Chirp 参数设计 | 1,526,460 | `F0368A0DD52331E817EF8D937E52D430F0ECE410B1FE1C9BF72E54663015BEEB` |
| SWRA554A | TDM-MIMO 原理 | 1,008,506 | `BAB44DA5463F3AA2F3C518A75E40051A242248BF6060A7B48FA9414A8D208B05` |

若需要离线副本，放入被忽略的 `references/cache/ti/`，并登记 URL、获取时间、字节数、SHA-256、许可和是否修改。

## 🔍 Checked non-source

`PKUFlyingPig/cs-self-learning` 是用户最初提供的线索。公开完整 tree 与文本扫描未发现该毫米波教程、作者或 mmWave 链接，因此记录为 `checked lead / not a direct source`，不能作为三份 MATLAB 文件的上游引用。[^9]

## 📋 Governance

1. 第三方代码和资料只进入 `references/`
2. 引用固定 commit 或文档 ID，不只记录可变首页
3. 本地副本必须登记来源、日期、bytes、SHA-256 和许可
4. 上游文件如有修改，另建 patch/adapter，不覆盖 provenance 基线；上述既有 `demo.m` 本地种子是迁移前遗留，已用双哈希和逐项差异单独登记
5. 每 6–12 个月或论文提交前复核关键 URL 与版本锁

## 🔗 References

[^1]: St. Zhang. (2024). "PKU Millimeter Wave Radar Tutorial." _GitHub_. https://github.com/StZhang-B/PKU-Millimeter-Wave-Radar-Tutorial

[^2]: St. Zhang. (2024). "Initial signal-processing commit 9cfc66d." _GitHub_. https://github.com/StZhang-B/PKU-Millimeter-Wave-Radar-Tutorial/commit/9cfc66de4879957b4a7ba42c088825c9836e1064

[^3]: St. Zhang. (2024). "MIT License." _GitHub_. https://github.com/StZhang-B/PKU-Millimeter-Wave-Radar-Tutorial/blob/9cfc66de4879957b4a7ba42c088825c9836e1064/LICENSE

[^4]: Texas Instruments. "IWR1443 Single-Chip 76- to 81-GHz mmWave Sensor Datasheet." https://www.ti.com/lit/ds/symlink/iwr1443.pdf

[^5]: Texas Instruments. "DCA1000EVM Data Capture Card User's Guide." https://www.ti.com/lit/ug/spruij4a/spruij4a.pdf

[^6]: Texas Instruments. "mmWave Radar Device ADC Raw Data Capture." https://www.ti.com/lit/an/swra581b/swra581b.pdf

[^7]: Texas Instruments. "Programming Chirp Parameters in TI Radar Devices." https://www.ti.com/lit/an/swra553a/swra553a.pdf

[^8]: Texas Instruments. "MIMO Radar." https://www.ti.com/lit/an/swra554a/swra554a.pdf

[^9]: PKUFlyingPig. "cs-self-learning." _GitHub_. https://github.com/PKUFlyingPig/cs-self-learning
