# 代码来源和参考资料

## 数据文件与运行环境

| 项目 | 值 |
| --- | --- |
| 原始数据 | `project/data/raw/adc_data.bin` |
| 大小 | 157,286,400 bytes |
| SHA-256 | `7EB0F8A619D23915C3F05DF5081F8D44F34BB2DD20CBBCE81C3881ED203681E7` |
| 历史 debug NPZ SHA-256 | `0D2F9273B9C32F9D0DB4E927EF887C9F8C774F323A793267C801B97FE986F7D1` |
| Python | 3.10.20 |
| NumPy / SciPy / Matplotlib | 2.2.5 / 1.15.3 / 3.10.8 |
| MkDocs / Material | 1.6.1 / 9.7.6 |

## MATLAB 代码从哪里来

本地 MATLAB 三件套属于 `StZhang-B/PKU-Millimeter-Wave-Radar-Tutorial` 代码族；上游明确面向 `IWR1843 + DCA1000`。

| 本地文件 | 固定上游关系 |
| --- | --- |
| `DCA1000_Read_Data.m` | 与固定提交逐字节一致，SHA-256 `EBD4F660...BEE14` |
| `generateParameter.m` | 与固定提交逐字节一致，SHA-256 `F4D7B5D8...31D38` |
| `demo.m` | 69 行中 66 行一致；本地增加两条 lint 注释并把数据盘符 C: 改为 D: |

本地 Python 的 `iwr1443` 命名是后续适配/扩展，不是上游教程的原始硬件标识。`PKUFlyingPig/cs-self-learning` 是最初的背景线索，但公开树与文本核验没有发现它是这三份 MATLAB 的直接来源。

## 官方硬件与信号处理资料

2026-10-15 核对的芯片接口差异：IWR1443 数据手册 SWRS211C §5.9.5 为 4 条 LVDS 数据 lane；IWR1843 数据手册 SWRS228B §7.10.4 为 2 条。两者均有 3 TX、4 RX。xWR14xx 的 I/Q 文件示例见 SWRA581B §5 图 9 与 §9.1；该 2018 年版本没有直接覆盖 IWR1843，所以不能仅凭同为双 lane 就把其他型号的完整格式当成 IWR1843 的通用规则。

本轮本地副本与校验记录位于 `references/cache/ti/README.md`。IWR1443 可变链接本次返回的版本与旧记录不同，旧记录保留，不据此判断哪份是最新版本。

1. [IWR1443 datasheet](https://www.ti.com/lit/ds/symlink/iwr1443.pdf) — 芯片与天线能力。
2. [DCA1000EVM User's Guide](https://www.ti.com/lit/ug/spruij4a/spruij4a.pdf) — 采集板与数据流。
3. [mmWave Radar Device ADC Raw Data Capture](https://www.ti.com/lit/an/swra581b/swra581b.pdf) — ADC/LVDS 原始格式。
4. [Programming Chirp Parameters in TI Radar Devices](https://www.ti.com/lit/an/swra553a/swra553a.pdf) — chirp 与尺度设计。
5. [MIMO Radar](https://www.ti.com/lit/an/swra554a/swra554a.pdf) — TDM-MIMO 原理。
6. [IWR1843 datasheet](https://www.ti.com/lit/ds/symlink/iwr1843.pdf) — IWR1843 的射频通道与 LVDS 接口。

## 教学写法参考

参考 [PySDR 的 I/Q 采样章](https://pysdr.org/content/sampling.html)和[频域章](https://pysdr.org/content/frequency_domain.html)：先让读者观察一个简单信号，再推公式、写小段代码验证。本教程按雷达采集和处理流程组织，代码同时提供 MATLAB 与 Python，没有复制其正文或插图。

## 上游代码与许可

- [PKU Millimeter Wave Radar Tutorial](https://github.com/StZhang-B/PKU-Millimeter-Wave-Radar-Tutorial)
- [固定信号处理提交 9cfc66d](https://github.com/StZhang-B/PKU-Millimeter-Wave-Radar-Tutorial/commit/9cfc66de4879957b4a7ba42c088825c9836e1064)
- [固定提交的 MIT License](https://github.com/StZhang-B/PKU-Millimeter-Wave-Radar-Tutorial/blob/9cfc66de4879957b4a7ba42c088825c9836e1064/LICENSE)
- [用户提供的背景线索 cs-self-learning](https://github.com/PKUFlyingPig/cs-self-learning)

完整文件校验值、TI PDF 版本记录与资料保存规则见项目 `references/README.md`。

## 记录实验时保留哪些信息

引用本 Wiki 时，应同时注明：

1. 当前输出使用 `processing_mode=strict_matlab`；
2. TDM candidate 只是更合理但未标定的布局假设；
3. 角度横轴与 bin 30 位移尚不具备定量物理效力；
4. 原始数据 hash、采集配置和所用代码版本。
