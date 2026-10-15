# 速度：比较多次观测之间的相位

距离 FFT 告诉我们回波落在哪个距离格。现在固定其中一格和一个通道，每轮取一个复数，得到 128 个点。目标沿雷达视线移动时，传播距离持续变化，这些点的相位会有规律地转动。

## 1. 从位移到多普勒频率

单站雷达的回波走一个来回。在选定符号约定下，距离变化 $\Delta R$ 对应相位变化 $4\pi\Delta R/\lambda$。若径向速度 v 近似恒定，$\Delta R=vt$，则：

\[
\phi(t)=\phi_0+\frac{4\pi v}{\lambda}t,
\qquad f_D=\frac{1}{2\pi}\frac{d\phi}{dt}=\frac{2v}{\lambda}.
\]

于是速度估计又变成了频率估计。但这次的采样间隔不是 ADC 的 0.1 µs，而是**同一个虚拟通道两次观测之间的时间**。

## 2. 三路 TX 轮发时，为什么要等三次

先用简单数字理解相位与速度：假设波长 4 mm，目标每 1 ms 移动 0.5 mm。回波路程每次增加 1 mm，也就是四分之一波长，因此相位依次转过 0、π/2、π、3π/2。每 4 ms 转一圈，频率为 250 Hz；代入 `v=λfD/2`，得到 `4 mm × 250 / 2 = 0.5 m/s`。

!!! info "IWR1843 不一定用 3Tc"
    三路轮发时，IWR1443 和 IWR1843 都应按同一 TX 的重复间隔换算。若只启用两路轮发就是 2Tc；单路重复才是 Tc。BPM 或更复杂的发射安排还需要相应解码。区别来自本次 chirp 配置，不是型号名称。

<ol class="tx-sequence" aria-label="每 160 微秒发射一次，TX1 每 480 微秒重复"><li><strong>TX1</strong><span>0 µs</span></li><li>TX2<span>160 µs</span></li><li>TX3<span>320 µs</span></li><li><strong>TX1</strong><span>480 µs</span></li></ol>

第一次和第四次才是 TX1 的两次观测。若采集确实如此轮发，慢时间间隔 $T_{\mathrm{slow}}=3T_c=480\,\mu s$。不同 TX 的相邻发射不能直接当成同一通道的连续采样。

\[
X_d[k,\ell,p]=\sum_{m=0}^{N_c-1}X_r[k,m,p]w_d[m]e^{-j2\pi\ell m/N_c},
\qquad v_\ell=\frac{\lambda\ell}{2N_cT_{\mathrm{slow}}}.
\]

移位后，偶数长度的有符号格编号为 $\ell=-N_c/2,\ldots,N_c/2-1$。由此得到速度格间距 $\Delta v=\lambda/(2N_cT_{\mathrm{slow}})$，无模糊速度区间为 $[-\lambda/(4T_{\mathrm{slow}}),\lambda/(4T_{\mathrm{slow}}))$。

| 用哪个间隔换算 | 每格速度 | 无模糊速度上限的量级 |
| --- | ---: | ---: |
| 当前代码的 160 µs | 0.09402 m/s | 6.017 m/s |
| 三路轮发的 480 µs | 0.03134 m/s | 2.006 m/s |

间隔变长，固定 128 点覆盖的时间更长，速度格更细；但采样率更低，能无歧义表示的最大速度也更小。[动手切换两种间隔](../orientation/parameters-and-shapes.md#hands-on)。

## 3. 先写一份处理所有通道的版本

输入尺寸为 `[距离格,轮次,通道]`，因此 Python 沿 `axis=1`，MATLAB 沿第 2 维。以下为教学实现，还没有替换项目原函数。

```python
nc = range_profile.shape[1]
w = np.hamming(nc).reshape(1, -1, 1)
D = np.fft.fftshift(np.fft.fft(range_profile * w, axis=1), axes=1)
tslow = 480e-6                 # 假定三路轮发
wavelength = 3e8 / (77e9 + 29.982e12*60e-6/2)
v_axis = wavelength * np.fft.fftshift(np.fft.fftfreq(nc, d=tslow)) / 2
```

```matlab
nc = size(rangeCube,2);
w = reshape(0.54-0.46*cos(2*pi*(0:nc-1)/(nc-1)),1,[],1);
D = fftshift(fft(rangeCube.*w,nc,2),2);
tslow = 480e-6;
wavelength = 3e8/(77e9+29.982e12*60e-6/2);
vAxis = wavelength*(-nc/2:nc/2-1)/(2*nc*tslow);
```

如果目标峰在中心右侧第 5 格，按三路轮发得到约 `5 × 0.03134 = 0.1567 m/s`。正号究竟表示靠近还是远离，要用已知运动方向验证。

## 4. 项目原函数与教学版差在哪里

```python linenums="259"
def run_doppler_fft_strict(range_profile: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    speed_profile = np.zeros_like(range_profile, dtype=np.complex128)
    doppler_window = make_window(cfg.doppler_window, cfg.chirps).reshape(1, -1, 1)
    temp = range_profile[:, :, : cfg.rx] * doppler_window
    # Strict MATLAB parity: Doppler FFT is only computed for channels 1:4.
    speed_profile[:, :, : cfg.rx] = np.fft.fftshift(
        np.fft.fft(temp, n=cfg.doppler_bin, axis=1),
        axes=1,
    )
    return speed_profile
```

源文件：`project/src/iwr1443_adc_utils.py`，函数 `run_doppler_fft_strict`。

数组先全部置零，然后只给 `:cfg.rx` 写入结果。`cfg.rx=4`，因此后 8 个通道始终为零。这是沿用 MATLAB 教程 `for k=1:parameter.rxNum` 的结果，并非多普勒理论要求。用于角度估计时，这个遗漏会继续传到下一步。

## 5. 移动目标为什么还需要 TX 时间补偿

TX2 比 TX1 晚发一个 $T_c$，TX3 晚发两个 $T_c$。移动目标在等待期间产生额外相位 $2\pi f_D\delta t_p$。如果把它全部当成天线位置造成的相位差，角度就会偏。

在已选中目标的距离—速度格后，若观测相位包含正号的多普勒项，可做：

\[
z_p^{\mathrm{comp}}=z_p\exp(-j2\pi\widehat f_D\delta t_p).
\]

```python
# z: 12 个通道在同一目标格的复数；假定 TX 分组顺序已确认
offsets = np.repeat(np.arange(3) * 160e-6, 4)
z_comp = z * np.exp(-1j * 2 * np.pi * fd_hat * offsets)
```

```matlab
% z 使用列向量，fdHat 来自目标所在的多普勒格
offsets = repelem((0:2)'*160e-6,4);
zComp = z(:).*exp(-1j*2*pi*fdHat*offsets);
```

TX 顺序、符号和速度模糊都影响补偿，不能只抄一个指数表达式。更多推导见 TI 的 [MIMO Radar](https://www.ti.com/lit/an/swra554a/swra554a.pdf)。

## 检查点

在模拟练习里，把 `tslow` 的换算值改小三倍，同时保持输入数据不变，估计速度应大三倍。若同时重造了一份不同相位的数据，就不是在单独测试时间轴错误了。下一章：[从天线相位差估计方向](angle.md)。
