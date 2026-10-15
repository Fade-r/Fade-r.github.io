# 速度测量

距离 FFT 之后，固定一个距离格和一个通道，每次该通道重复观测时取出该格的复数值。目标运动会使这串复数的相位随时间变化，多普勒 FFT 用于估计这种变化的频率。

!!! formula-recap "距离 FFT 输出中保留了什么"

    [距离测量](range.md)的输出记为 $X_r[k,m,p]$，三个下标分别是距离格、轮次和通道。固定目标格 $k_0$ 与通道 $p_0$，得到：

    \[
    z[m]=X_r[k_0,m,p_0].
    \]

    这串复数就是本章的输入。一次 chirp 内的采样点 $n$ 已经经过 FFT；现在考察的是不同轮次 $m$ 之间的相位变化。

这里测得的是**径向速度**：目标沿雷达与目标连线方向的速度分量，而不是任意方向的总速度。

## 位移与相位

!!! formula-recap "从拍频相位中取出距离项"

    [混频推导](../foundations/echo-and-mixing.md)给出
    $\phi_b(t)=2\pi f_bt+2\pi(f_0\tau-S\tau^2/2)$，其中 $\tau=2R/c$。
    载频对应的距离相位为 $2\pi f_0\tau=4\pi f_0R/c$。用参考载频 $f_c$ 和波长 $\lambda=c/f_c$ 表示，即为 $4\pi R/\lambda$。

    本章采用常用的窄带、帧内小位移近似：主要跟踪这项随轮次的变化，暂不计运动对单次 chirp 拍频和距离格位置的影响。

电磁波传播一个波长 $\lambda$，相位变化 $2\pi$。目标远离雷达 $\Delta R$，往返路程增加 $2\Delta R$，因此按本教程的解调约定：

\[
\Delta\phi=2\pi\frac{2\Delta R}{\lambda}
=\frac{4\pi\Delta R}{\lambda}.
\]

若径向速度 $v$ 恒定，经过时间 $t$ 后 $\Delta R=vt$。这里的 $t$ 从首次观测起累计，不再是每个 chirp 内重新计时的快时间：

\[
\phi(t)=\phi_0+\frac{4\pi v}{\lambda}t
=\phi_0+2\pi f_Dt.
\]

比较两式可得多普勒频率：

\[
f_D=\frac{2v}{\lambda},\qquad v=\frac{\lambda f_D}{2}.
\]

例如波长近似为 4 mm，目标每毫秒远离 0.5 mm。往返路程每毫秒增加 1 mm，即四分之一波长，相位每次增加 $\pi/2$。4 ms 转一圈，所以 $f_D=250$ Hz，速度为 0.5 m/s。

## 慢时间采样

设同一通道的重复间隔为 $T_{\mathrm{slow}}$，把 $t=mT_{\mathrm{slow}}$ 代入上式，再用 $z=Ae^{j\phi}$ 表示复数值：

\[
z[m]=A e^{j(\phi_0+2\pi f_DmT_{\mathrm{slow}})}.
\]

其中 $A$ 是该距离格的幅度，$\phi_0$ 是第一次慢时间观测的相位，已包含传播、反射等固定相位，不仅是发射信号的初相位。这与估计拍频的形式相同，只是采样间隔由 $1/F_s$ 换成了 $T_{\mathrm{slow}}$。

### Python 示例

```python
import numpy as np

wavelength = 3e8/77e9
tslow, nc, fd = 1e-3, 64, 125.0
m = np.arange(nc)
z = np.exp(1j*2*np.pi*fd*m*tslow)

D = np.fft.fftshift(np.fft.fft(z))
f_axis = np.fft.fftshift(np.fft.fftfreq(nc, d=tslow))
index = np.argmax(np.abs(D))
v = wavelength*f_axis[index]/2
print(f_axis[index], round(v, 3))
```

### MATLAB 示例

```matlab
wavelength = 3e8/77e9;
tslow = 1e-3; nc = 64; fd = 125;
m = 0:nc-1;
z = exp(1j*2*pi*fd*m*tslow);

D = fftshift(fft(z));
fAxis = (-nc/2:nc/2-1)/(nc*tslow);
[~, index] = max(abs(D));
v = wavelength*fAxis(index)/2;
disp([fAxis(index), round(v,3)]);
```

结果为 125 Hz、约 0.244 m/s。代码使用 77 GHz 对应的波长，不使用前面心算时近似的 4 mm。

<figure><img src="../assets/lessons/doppler-peak.svg" alt="理想多普勒频谱对应的速度峰在约0.244米每秒处"><figcaption>零速度位于中央，正负速度分列两侧。示例以远离为正；实测符号应通过已知方向的运动确认。</figcaption></figure>

## 速度轴与无模糊范围

!!! formula-recap "慢时间信号与测速换算"

    \[
    z[m]=Ae^{j(\phi_0+2\pi f_DmT_{\mathrm{slow}})},\qquad
    v=\frac{\lambda f_D}{2}.
    \]

    $N_c$ 次观测组成一帧的慢时间序列。下面先用 DFT 估计 $f_D$，再把频率格换算成速度。

慢时间序列代入 DFT 后，初始相位与幅度可以提出求和号：

\[
\begin{aligned}
D[\ell]
&=\sum_{m=0}^{N_c-1}A e^{j(\phi_0+2\pi f_DmT_{\mathrm{slow}})}
e^{-j2\pi\ell m/N_c}\\
&=A e^{j\phi_0}\sum_{m=0}^{N_c-1}
e^{j2\pi m(f_DT_{\mathrm{slow}}-\ell/N_c)}.
\end{aligned}
\]

当 $f_DT_{\mathrm{slow}}=\ell/N_c$ 时，每项指数都为 1，得到峰值 $N_cA e^{j\phi_0}$。于是：

\[
f_{D,\ell}=\frac{\ell}{N_cT_{\mathrm{slow}}},
\qquad
v_\ell=\frac{\lambda}{2}f_{D,\ell}
=\frac{\lambda\ell}{2N_cT_{\mathrm{slow}}}.
\]

移位后，对于偶数 $N_c$，有符号频率格编号 $\ell$ 从 $-N_c/2$ 到 $N_c/2-1$。速度轴为：

\[
v_\ell=\frac{\lambda\ell}{2N_cT_{\mathrm{slow}}}.
\]

相邻速度格间隔为 $\lambda/(2N_cT_{\mathrm{slow}})$。无模糊范围也可以从相位增量理解。相邻观测间：

\[
\Delta\phi=2\pi f_DT_{\mathrm{slow}}
=\frac{4\pi vT_{\mathrm{slow}}}{\lambda}.
\]

采样无法区分相差 $2\pi$ 整数倍的相位增量。采用 $[-\pi,\pi)$ 作为主值区间，把 $\Delta\phi$ 代入并乘以正数 $\lambda/(4\pi T_{\mathrm{slow}})$，得到：

\[
-\frac{\lambda}{4T_{\mathrm{slow}}}
\le v<
\frac{\lambda}{4T_{\mathrm{slow}}}.
\]

增加观测次数可以细化速度格；增加重复间隔也会细化速度格，但会缩小无模糊速度范围。

## 整帧多普勒 FFT

输入 `range_cube` 的维度为 `[距离格,轮次,通道]`，沿第二维计算：

```python
nc = range_cube.shape[1]
window = np.hamming(nc).reshape(1, nc, 1)
doppler_cube = np.fft.fftshift(
    np.fft.fft(range_cube * window, axis=1), axes=1)
```

```matlab
nc = size(rangeCube,2);
window = reshape(0.54-0.46*cos(2*pi*(0:nc-1)/(nc-1)),1,[],1);
dopplerCube = fftshift(fft(rangeCube.*window,nc,2),2);
```

输出记为 $D[k,\ell,p]$，三个维度是距离格、速度格和通道，对应 `doppler_cube`。每个通道都沿自己的轮次序列处理；各通道的复数结果保留下来，供后面的测角使用。

## TDM 发射间隔

3 路 TX 轮流发射时，若相邻实际 chirp 间隔为 160 µs，则顺序为：

| 时刻 / µs | 0 | 160 | 320 | 480 |
| --- | --- | --- | --- | --- |
| 发射通道 | TX1 | TX2 | TX3 | TX1 |

TX1 每 480 µs 才重复一次，因此 $T_{\mathrm{slow}}=480$ µs。若误用 160 µs，同一个频谱峰会被换算成 3 倍速度。

IWR1443 与 IWR1843 都按实际发射时序计算这个间隔。单 TX、双 TX 轮发、三 TX 轮发以及 BPM 编码不能混用同一个时间参数。TDM 对测角相位的影响见[角度测量](angle.md)。

若目标在观测期间明显跨越距离格，固定一格就不能持续取得同一个目标，需先做目标跟踪或距离迁移校正。运动也会改变单次扫频的拍频：在相同符号约定和一阶近似下，$f_b\approx2SR/c+f_D$。若仍直接用静止目标公式换算：

\[
\widehat R=\frac{cf_b}{2S}
\approx R+\frac{cf_D}{2S}.
\]

最后一项是速度造成的距离偏移，这就是距离—速度耦合。得到可靠的 $f_D$ 后，可先从拍频中减去它，再换算距离。本章短例忽略了这一小量，并假设一帧内速度近似恒定。

参考：[TI MIMO Radar](https://www.ti.com/lit/an/swra554a/swra554a.pdf)。
