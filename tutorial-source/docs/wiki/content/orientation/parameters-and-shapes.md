# 项目参数对照

基础章节使用便于核算的示例参数。本页列出原处理程序中的实际设置，用于将公式与代码对应。

## 采集参数

参数定义位于 `project/src/iwr1443_adc_utils.py` 的 `RadarConfig`，入口配置位于 `process_iwr1443_adc.py`。

| 代码名 | 原程序值 | 含义 |
| --- | --- | --- |
| `start_freq` | 77 GHz | 扫频起始频率 |
| `slope` | 29.982 MHz/µs | 扫频斜率 |
| `tr` | 60 µs | 扫频时长 |
| `idle_time` | 100 µs | 空闲时间 |
| `fs` | 10 MHz | ADC 采样率 |
| `samples` | 256 | 每 chirp 的采样点数 |
| `chirps` | 128 | 按 TDM 解释时，每 TX 的重复次数 |
| `tx`、`rx` | 3、4 | 发射、接收通道数 |
| `tframe_set` | 80 ms | 帧起点间隔 |

这些值来自处理代码。原始采集配置尚未完整归档，不能仅因文件长度吻合就认定它们全部正确。

## 派生参数 { #hands-on }

相邻实际 chirp 的间隔：

\[
T_c=60+100=160\ \mu s.
\]

ADC 采样时长：

\[
T_{\mathrm{ADC}}=\frac{256}{10\ \mathrm{MHz}}=25.6\ \mu s.
\]

采样覆盖带宽：

\[
B_{\mathrm{ADC}}=29.982\times25.6\approx768\ \mathrm{MHz}.
\]

因此未补零的距离格间隔约为：

\[
\Delta R=\frac{c}{2B_{\mathrm{ADC}}}\approx0.195\ \mathrm m.
\]

原代码用完整扫频中点频率计算波长，得到约 3.851 mm。准确的相位模型还需结合实际 ADC 开始时刻和采样频段；该波长在这里是原程序使用的换算值。

若 TX1、TX2、TX3 轮流发射，同一 TX 间隔是 $3T_c=480$ µs。原速度轴使用 160 µs，相同格编号会被换算成 3 倍速度。

## 参数计算代码

原程序表达式：

```python
self.tc = self.tr + self.idle_time
self.bandwidth = self.slope * self.tr
self.bandwidth_valid = self.samples / self.fs * self.slope
self.center_freq = self.start_freq + self.bandwidth / 2.0
self.lambda_m = self.c / self.center_freq
self.range_resolution_m = self.c / (2.0 * self.bandwidth_valid)
self.speed_resolution_mps = self.lambda_m / (2.0 * self.doppler_bin * self.tc)
```

MATLAB 对应写法：

```matlab
tc = tr + idle_time;
bandwidth = slope*tr;
bandwidthValid = samples/fs*slope;
centerFreq = startFreq + bandwidth/2;
wavelength = c/centerFreq;
rangeResolution = c/(2*bandwidthValid);
speedResolution = wavelength/(2*chirps*tc);
```

最后一行保留了原程序的 `tc`，不是三路轮发时推荐的时间参数。原函数问题汇总见[代码分析](../code/code-map.md)。

## 数据尺寸

按原程序配置，一帧应包含：

\[
256\times128\times12=393216
\]

个复数，即 786432 个 int16 整数，占 1572864 字节。现有文件长度对应 100 帧。

| 数组 | 维度顺序 | 尺寸 |
| --- | --- | --- |
| `adc_cube` | 帧、通道、轮次、采样点 | `100 × 12 × 128 × 256` |
| `selected_frame` | 采样点、轮次、通道 | `256 × 128 × 12` |
| `range_profile` | 距离格、轮次、通道 | `256 × 128 × 12` |
| `speed_profile` | 距离格、速度格、通道 | `256 × 128 × 12` |
| `angle_profile` | 距离格、速度格、空间频率格 | `256 × 128 × 180` |

原多普勒函数只写入前 4 个通道，后 8 个为零；角度函数取前 8 个通道，所以其中只有 4 个有有效多普勒结果。数组尺寸并不等于有效通道数。

IWR1843 使用这些代码时，同样需要重新填写本次采集参数，并核对 LVDS 格式和阵列位置。
