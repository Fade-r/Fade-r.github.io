# 雷达与数据采集

雷达芯片完成发射、接收、混频和 ADC 采样。采集卡把 ADC 数据传到电脑，电脑保存数据，供 MATLAB 或 Python 离线处理。

## 雷达、采集卡和电脑

使用 DCA1000 采集原始数据时，三个设备的职责如下：

| 设备 | 作用 |
| --- | --- |
| 雷达开发板 | 产生扫频信号，接收回波，输出 ADC 采样值 |
| DCA1000 采集卡 | 接收雷达的 LVDS 数据，打包并经以太网发送 |
| 电脑 | 配置采集过程，接收数据包，保存文件并运行处理程序 |

LVDS 是雷达输出高速数字数据的电气接口。它传输的是采样结果，不是空中的毫米波信号。串口输出的点云则通常已经经过芯片内部处理，与原始 ADC 数据不同。

## 配置一次采集

实际操作可分为以下步骤。接口名称与开关位置应以开发板手册及所用 mmWave Studio 版本为准。[^1]

1. 连接雷达板、DCA1000 和电脑，检查供电、启动模式及网卡设置。
2. 选择接收天线，设置实数或复数 ADC 模式、有效位数和 LVDS 输出格式。
3. 设置起始频率、扫频斜率、扫频时长、ADC 开始时刻、采样率和采样点数。
4. 设置 chirp 序列，包括每次发射启用的 TX；设置每帧循环次数、帧周期和帧数。
5. 配置 DCA1000 的接收与保存，先使采集端就绪，再启动雷达帧。
6. 等待传输完成，保存数据、雷达配置和丢包日志。

**TX** 表示发射通道，**RX** 表示接收通道。每次发射可由多个 RX 同时接收。多路 TX 依次发射的方式称为 TDM，后面测速时需要使用同一 TX 两次发射之间的间隔。

## 采样时间与扫频时间

ADC 通常只在扫频中的一段时间采样。采 $N_s$ 个点、采样率为 $F_s$ 时，采样时长按 $N_s/F_s$ 计算：

\[
T_{\mathrm{ADC}}=\frac{N_s}{F_s},\qquad
B_{\mathrm{ADC}}=S T_{\mathrm{ADC}}.
\]

例如 $N_s=256$、$F_s=8$ MHz，采样时长为 32 µs。斜率为 30 MHz/µs，则采样覆盖的带宽为 960 MHz。即使完整扫频持续 40 µs，后续距离分辨率计算也要使用 ADC 实际覆盖的带宽。

最后一个采样点位于开始采样后的 $(N_s-1)/F_s$；$N_s/F_s$ 是频谱分析使用的记录时长。配置时还要满足 ADC 开始延时加采样时长不超过可用采样区间。[^2]

### Python 示例

```python
ns = 256
fs = 8e6
slope = 30e12
adc_time = ns / fs
bandwidth = slope * adc_time
print(f"{adc_time*1e6:.0f} us, {bandwidth/1e6:.0f} MHz")
```

### MATLAB 示例

```matlab
ns = 256;
fs = 8e6;
slope = 30e12;
adcTime = ns/fs;
bandwidth = slope*adcTime;
fprintf('%.0f us, %.0f MHz\n', adcTime*1e6, bandwidth/1e6);
```

结果为 `32 us, 960 MHz`。

## 数据量检查

复数采样保存 I、Q 两个分量。若每个分量使用 2 字节存储，则每个复数占 4 字节。

假设 4 路 RX、3 路 TX 依次发射，每个 TX 重复 64 次，每次采 256 点，一帧的纯 ADC 数据量为：

\[
256\times64\times3\times4\times4=786432\ \text{字节}.
\]

这是四路接收均启用、没有额外数据段时的计算。实际格式若包含包头、填充或其他数据段，需要另行计入。

文件长度可以检查少帧或参数不一致，但不能排除丢包后补零。丢包日志必须一同保留。

## 网络数据与 ADC 数据

以 SWRA581B 描述的 mmWave Studio 流程为例，网络接收数据需要经过数据包重排、缺失数据补零和元数据移除，才能得到按 ADC 格式排列的数据。处理前应确认采集软件是否已经完成这些操作，避免重复处理。[^3]

从此处开始，后续读取示例使用已经整理好的纯 ADC 文件。

## IWR1443 与 IWR1843

两种芯片均有 3 路 TX、4 路 RX，但支持的 LVDS 数据通道数不同：IWR1443 为 4，IWR1843 为 2。这里的 LVDS 通道不是天线数量。[^4][^5]

解析数据时，应按芯片、ADC 模式、lane 配置和 I/Q 顺序选择格式，不能只把程序中的芯片名称替换一下。两种开发板的天线位置也要分别确认。

[^1]: TI. [DCA1000EVM 用户手册](https://www.ti.com/lit/ug/spruij4a/spruij4a.pdf).
[^2]: TI. [Programming Chirp Parameters](https://www.ti.com/lit/an/swra553a/swra553a.pdf).
[^3]: TI. [ADC Raw Data Capture，SWRA581B](https://www.ti.com/lit/an/swra581b/swra581b.pdf)，第 9 节。
[^4]: TI. [IWR1443 数据手册](https://www.ti.com/lit/ds/symlink/iwr1443.pdf)，本地核验版本 SWRS211C，§5.9.5。
[^5]: TI. [IWR1843 数据手册](https://www.ti.com/lit/ds/symlink/iwr1843.pdf)，本地核验版本 SWRS228B，§7.10.4。
