# 距离：从一次扫频中找出拍频

上一章得到了一帧复数数据。这一章固定一轮、一个通道，只看其中的 256 个采样点。目标越远，回波回来得越晚；FMCW 雷达利用这段延迟，把距离变成一种容易测量的频率差。

## 1. 为什么距离会变成频率

发射频率按斜率 S 上升：$f_{\mathrm{tx}}(t)=f_0+St$。距离 R 的静止目标产生约 $\tau=2R/c$ 的往返延迟，所以同一接收时刻，回波对应的是较早发出的、频率稍低的信号。

<div class="axis-lessons"><section><h3>发出去</h3><p>频率持续上升：f₀ + St。</p></section><section><h3>反射回来</h3><p>延迟 τ 后到达：此刻收到的是 t−τ 时发出的信号。</p></section><section><h3>混频后取差频</h3><p>两者频率差为 Sτ = 2SR/c。这就是用来测距的拍频。</p></section></div>

例如 R=5 m，往返只需约 33.3 ns。直接精确计时很困难，但用本项目的斜率，会得到约 0.9994 MHz 的拍频，可以从 ADC 序列的频谱中估计。参见 TI 的 [chirp 参数说明](https://www.ti.com/lit/an/swra553a/swra553a.pdf)。

## 2. 把这句话写成公式

频率表示相位每秒转过多少圈，所以相位等于频率对时间的积分：`2π × ∫(f₀ + St)dt`。积分后得到下面的 `f₀t + St²/2`。

发射信号的复数表示为：

\[
s_{\mathrm{tx}}(t)=A\exp\{j2\pi[f_0t+St^2/2]\}.
\]

以 $s_{\mathrm{tx}}(t)s^*_{\mathrm{rx}}(t)$ 为解调约定，静止目标的相位差为：

\[
\phi_b(t)=2\pi[f_0\tau+St\tau-S\tau^2/2].
\]

这一步就是用发射相位减去延迟回波的相位：先把回波中的 t 换成 `t−τ`，展开平方 `(t−τ)²=t²−2tτ+τ²`，相减后 t² 项抵消，留下随 t 线性变化的 `Stτ`。因此每秒增加的相位除以 $2\pi$，就是 $f_b=S\tau$。采用相反的复数混频约定会改变符号。

用整齐的数算一次：令斜率为 30 MHz/µs，目标在 5 m，往返延迟约 1/30 µs，拍频就是 `30 × (1/30) = 1 MHz`。距离变成 10 m，延迟和拍频一起加倍。项目实际斜率为 29.982 MHz/µs，与这个教学数值很接近。

移动目标还带来多普勒项。在符号约定一致、单次扫频内位移足够小的近似下，$f_b\approx2SR/c+f_D$，其中 $f_D=2v/\lambda$。本章测距先忽略速度项；高速或高精度测量时需考虑距离—速度耦合。

## 3. 距离 FFT 怎样写

固定轮次 m 和通道 p，对采样点 n 求和：

\[
X_r[k,m,p]=\sum_{n=0}^{N_s-1}x[n,m,p]w_r[n]e^{-j2\pi kn/N_s}.
\]

这里 k 是频率格，不是米。项目的实际函数为：

```python linenums="247"
def run_range_fft(frame_cube_matlab: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    if frame_cube_matlab.shape != (cfg.samples, cfg.chirps, cfg.virtual_channels):
        raise ValueError(
            "run_range_fft expects MATLAB-view shape "
            f"({cfg.samples}, {cfg.chirps}, {cfg.virtual_channels}), got {frame_cube_matlab.shape}."
        )
    range_window = make_window(cfg.range_window, cfg.samples).reshape(-1, 1, 1)
    windowed = frame_cube_matlab * range_window
    # Range FFT is applied along the ADC-sample dimension to match the MATLAB implementation.
    return np.fft.fft(windowed, n=cfg.range_bin, axis=0)
```

源文件：`project/src/iwr1443_adc_utils.py`，函数 `run_range_fft`。

先验证尺寸；再把窗变成 `[256,1,1]`，乘到每轮、每通道上；最后沿 `axis=0` 计算 FFT。输出仍为 `[256,128,12]`，但第一维已经从采样时间变成拍频格。

MATLAB 教学实现：

```matlab
ns = size(frame,1);
wr = reshape(0.54-0.46*cos(2*pi*(0:ns-1)/(ns-1)),[],1,1);
rangeCube = fft(frame.*wr,ns,1);
```

## 4. 从格编号换成米

本项目没有对距离 FFT 补零，$N_{\mathrm{FFT}}=N_s=256$。因此：

\[
f_k=\frac{kF_s}{N_s},\qquad R_k=\frac{cf_k}{2S},\qquad
\Delta R=\frac{cF_s}{2SN_s}=0.195430\ \mathrm{m}.
\]

Python：

```python
fs, slope, c = 10e6, 29.982e12, 3e8
range_axis = np.arange(256) * c * fs / (2 * slope * 256)
k = np.argmax(np.abs(range_profile[:128, 0, 0]))
range_m = range_axis[k]
```

MATLAB：

```matlab
fs = 10e6; slope = 29.982e12; c = 3e8;
rangeAxis = (0:255)*c*fs/(2*slope*256);
[~, idx] = max(abs(rangeCube(1:128,1,1)));
rangeM = rangeAxis(idx);
```

这里为了练习，假设正距离目标位于正拍频一侧，只搜索前 128 格。真实数据必须核实符号和有效拍频范围；不能把完整复数 FFT 后半段都当作更远的目标。

## 5. 0.195 m 从哪里来，会不会太粗

!!! info "IWR1443 / IWR1843：公式相同，参数重新代入"
    两者都用实际 ADC 采样率、采样点数和扫频斜率计算距离轴。不要沿用另一块板的默认 profile，也不要把芯片可支持的总带宽直接当作这次 ADC 实际覆盖的带宽。

ADC 采样覆盖 $256/10\,\mathrm{MHz}=25.6\,\mu s$，有效带宽是 $S\times25.6\,\mu s=767.5392\,\mathrm{MHz}$，所以 $c/(2B_{\mathrm{valid}})\approx0.19543$ m。完整 60 µs 斜坡有 1.79892 GHz 带宽，但本段 ADC 没有采满这段时间，不能用完整带宽替代。

这给出未加窗理想情况下的距离分辨尺度。Hamming 窗会拓宽主瓣；补零会细化格点；单个强目标的峰位置也可能做亚格估计。这些都不等于把两个任意接近的目标可靠分开。后面用相位测微位移，则是跟踪同一个散射体的变化，和分开两个目标是不同问题。

## 6. 怎样读本项目的距离图

<figure><img src="../assets/figures/range_profile_frame000_chirp000_vc00.png" alt="单轮单通道的距离频谱"><figcaption>先看横轴的距离格，再看纵轴的 FFT 幅度。这里没有做功率标定；峰高只能在相同处理设置下比较。后半复频率段的距离标注还需核实。</figcaption></figure>

<figure><img src="../assets/figures/average_range_profile.png" alt="跨帧平均距离谱出现等间距重复峰"><figcaption>找相邻重复峰的间隔：约 64 格，也就是约 12.5 m。如此规则的重复，加上数据连续性检查，提示应优先检查排列方式。不能直接解释成多个真实目标。</figcaption></figure>

## 检查点

在[完整模拟练习](../practice/end-to-end.md)中，理论目标设置在第 14 格。你应得到 `14 × 0.19543 ≈ 2.736 m`。把目标移到第 20 格，检查谱峰和米数是否同时变化。下一章：[固定距离格，看相位如何随轮次变化](doppler.md)。
