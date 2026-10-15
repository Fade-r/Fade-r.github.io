# 逐张读懂现有的 13 张图

这些图片来自项目原有的 `strict_matlab` 处理结果。本页按处理顺序排列，每张先说明坐标，再指出该观察什么。图中幅度没有完成物理功率标定，单位只用于相同设置下的数值比较。

## 1. 原始整数：先看文件顺序

<figure><img loading="lazy" src="../assets/figures/raw_int16_segment.png" alt="原始整数：先看文件顺序"><figcaption>横轴是整数在文件中的编号，纵轴是原始数值。先看是否饱和或长时间恒为零；下半图只是奇偶位置拆分，不是 I/Q。</figcaption></figure>

[回到原理与代码](../data/adc-iq-layout.md)。

## 2. 一次扫频：看 I、Q、幅度和相位

<figure><img loading="lazy" src="../assets/figures/signal_frame000_chirp000_vc00.png" alt="一次扫频：看 I、Q、幅度和相位"><figcaption>横轴沿同一次扫频的采样点变化。先看 I、Q 是否有连续结构，再看幅度和相位；幅度接近零时，相位跳动通常不可靠。这里仍使用教程排列。</figcaption></figure>

[回到原理与代码](../data/adc-iq-layout.md)。

## 3. I/Q 散点：看复数分布

<figure><img loading="lazy" src="../assets/figures/iq_constellation_frame000_chirp000_vc00.png" alt="I/Q 散点：看复数分布"><figcaption>横轴 I、纵轴 Q，每个点是一对采样值。它可以显示中心偏移和幅度分布，但点的时间顺序已经丢失。不能仅凭散点像圆就认定相位测量正确。</figcaption></figure>

[回到原理与代码](../foundations/signal-and-fft.md)。

## 4. 单次距离谱：找频率峰

<figure><img loading="lazy" src="../assets/figures/range_profile_frame000_chirp000_vc00.png" alt="单次距离谱：找频率峰"><figcaption>横轴是代码换算出的距离，纵轴是未标定的 FFT 幅度。先找峰，再核对正负频率范围；完整 FFT 的后半段不能直接当作更远距离。</figcaption></figure>

[回到原理与代码](../processing/range.md)。

## 5. 平均距离谱：看重复峰

<figure><img loading="lazy" src="../assets/figures/average_range_profile.png" alt="平均距离谱：看重复峰"><figcaption>这是跨轮次和帧的幅度平均。重点看相邻重复峰约 64 格的间隔，而不是先把每个峰命名为目标。平均能稳定图形，也会稳定由错误排列产生的结构。</figcaption></figure>

[回到原理与代码](../processing/range.md)。

## 6. 距离—时间图：看结构是否持续

<figure><img loading="lazy" src="../assets/figures/range_time_vc00.png" alt="距离—时间图：看结构是否持续"><figcaption>横轴是帧编号，另一轴是距离，颜色表示每帧的平均幅度。水平条纹说明某个距离格长期较强，但可能是稳定背景或重复伪影；这张图没有目标关联和跟踪。</figcaption></figure>

[回到原理与代码](../audit/scientific-audit.md)。

## 7. 相位和位移：先看信号质量

<figure><img loading="lazy" src="../assets/figures/slow_time_rangebin030_vc00.png" alt="相位和位移：先看信号质量"><figcaption>按 I/Q、相位、位移的顺序往下读。位移只是相位乘上 λ/(4π) 后的结果，不会自动过滤错误相位。第 30 格较弱，目前几十毫米曲线缺少真实运动依据。</figcaption></figure>

[回到原理与代码](../processing/phase.md)。

## 8. 跨帧频谱：检查时间轴

<figure><img loading="lazy" src="../assets/figures/doppler_spectrum_rangebin030_vc00.png" alt="跨帧频谱：检查时间轴"><figcaption>横轴是按 160 µs 插值网格得到的频率，纵轴是频谱幅度。约 74% 的点由帧间插值补出，因此不要把这些峰当成标准单帧 Doppler 结果。</figcaption></figure>

[回到原理与代码](../processing/phase.md)。

## 9. 时频图：看频谱随时间变化

<figure><img loading="lazy" src="../assets/figures/spectrogram_rangebin030_vc00.png" alt="时频图：看频谱随时间变化"><figcaption>一个方向是时间，另一个是频率，颜色表示短时频谱强弱。周期竖条可能与帧间空隙和插值有关；约 24.4 Hz 的频率格间距不足以研究亚赫兹运动。</figcaption></figure>

[回到原理与代码](../processing/phase.md)。

## 10. 十二通道 I/Q：看通道差异

<figure><img loading="lazy" src="../assets/figures/channel_iq_grid_rangebin030.png" alt="十二通道 I/Q：看通道差异"><figcaption>每个小图对应一个通道的 I/Q 轨迹。先核对每幅图坐标范围，自动缩放会让不同幅度看起来相似；跨帧连线也不能当作空隙内真实轨迹。</figcaption></figure>

[回到原理与代码](../processing/phase.md)。

## 11. 十二通道相位：看是否稳定

<figure><img loading="lazy" src="../assets/figures/channel_phase_grid_rangebin030.png" alt="十二通道相位：看是否稳定"><figcaption>每个小图显示同一距离格的通道相位。绝对相位偏置和解缠选择的圈数可能不同，不要只比较曲线高低；先比较变化是否一致以及信号是否足够强。</figcaption></figure>

[回到原理与代码](../processing/phase.md)。

## 12. 通道相干矩阵：看复数序列是否相似

<figure><img loading="lazy" src="../assets/figures/channel_correlation_rangebin030.png" alt="通道相干矩阵：看复数序列是否相似"><figcaption>横纵轴都是通道编号，数值越接近 1，表示两个复数序列的归一化内积模越大。当前非零序列与自身比较为 1；低非对角值可能来自噪声、排列错误或相位变化，不能单独定位原因。</figcaption></figure>

[回到原理与代码](../code/code-map.md)。

## 13. 距离—空间频率图：先别把横轴当角度

<figure><img loading="lazy" src="../assets/figures/range_angle_heatmap_strict.png" alt="距离—空间频率图：先别把横轴当角度"><figcaption>横轴是空间 FFT 格，纵轴是代码换算出的距离，颜色来自对 Doppler 维的幅度求和。输入仅 4 个通道有效，另 4 个为零；阵列和角度轴尚未校准。</figcaption></figure>

[回到原理与代码](../processing/angle.md)。

## 自己画图时，先把单位写进坐标

以单轮距离谱为例，下面假定已经有距离轴和距离 FFT 数组：

```python
import matplotlib.pyplot as plt
plt.plot(range_axis[:128], np.abs(range_profile[:128,0,0]))
plt.xlabel('Range (m)')
plt.ylabel('FFT magnitude (a.u.)')
plt.grid(True)
plt.show()
```

```matlab
plot(rangeAxis(1:128),abs(rangeCube(1:128,1,1)));
xlabel('Range (m)'); ylabel('FFT magnitude (a.u.)'); grid on;
```

同时写下选了哪一帧、哪一轮、哪个通道，用了什么窗和哪种数据排列。比较两种算法时保持横纵轴范围一致，否则自动缩放容易造成误判。
