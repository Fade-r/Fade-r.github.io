# 方向：比较不同天线收到的相位

做完距离和多普勒处理后，我们可以固定一个距离—速度格，从多个通道各取一个复数。不同天线的位置不同，回波到达它们的路程略有差别，于是留下相位差。这一章解释如何把这种差别换成角度。

## 1. 相邻天线为什么出现相位差

先考虑远场平面波、等间距直线阵列。角度 θ 从阵列正前方量起，阵元间距为 d。相邻阵元的路程差大小为 $d\sin\theta$。按选定的天线编号与相位正方向：

\[
z_p=A\exp\left(j\frac{2\pi}{\lambda}pd\sin\theta\right),
\qquad \Delta\phi=\frac{2\pi d}{\lambda}\sin\theta.
\]

正前方 θ=0，各阵元相位相同；偏离正前方后，相位沿阵元编号逐渐增加或减小。若 $d=\lambda/2$，30° 对应相邻相位差 π/2。于是跨天线的序列也像一个复正弦，可以用 FFT 找出它的“空间频率”。

这里先讲理想均匀线阵。IWR1443 的 TX/RX 组合必须根据天线实际位置换算成虚拟阵元位置，不能仅因为有 12 个通道，就直接套上 12 元水平线阵。

## 2. 空间 FFT 的横轴先是格编号

对 P 个已校准阵元做 $N_\theta$ 点 FFT：

\[
X_a[q]=\sum_{p=0}^{P-1}z_p\exp(-j2\pi qp/N_\theta).
\]

信号本身每个阵元增加的相位是 $2\pi d\sin\theta/\lambda$。在峰位置，它应接近 FFT 模板的 $2\pi q/N_\theta$，所以：

\[
\sin\theta_q=\frac{\lambda q}{dN_\theta},
\qquad d=\lambda/2\Rightarrow\theta_q=\arcsin(2q/N_\theta).
\]

因此 180 个 FFT 格不等于 −90° 到 +89°。角度轴要经过反正弦，格点在角度上并不等间隔。补零到 180 点只让谱线更细，分辨能力主要仍由实际孔径和加窗决定。

## 3. 两种语言的教学写法

下面假定你已选出一个目标、得到一维向量 `z`，且这些通道组成校准后的半波长均匀线阵；运动目标的 TX 时刻差也已补偿。

```python
n_angle = 180
A = np.fft.fftshift(np.fft.fft(z, n=n_angle))
q = np.arange(-n_angle//2, n_angle//2)
theta = np.degrees(np.arcsin(2*q/n_angle))
peak = np.argmax(np.abs(A))
theta_hat = theta[peak]
```

```matlab
nAngle = 180;
A = fftshift(fft(z(:),nAngle));
q = -nAngle/2:nAngle/2-1;
theta = asind(2*q/nAngle);
[~, peak] = max(abs(A));
thetaHat = theta(peak);
```

在完整模拟练习里，空间峰被设为 `q=45`，因此先算 `2 × 45 / 180 = 1/2`，再取反正弦，得到 30°。你可以改这个编号来验证公式。

## 4. 实际阵列不等间距怎么办

!!! info "IWR1443 / IWR1843：测角要看开发板天线"
    芯片的 3 TX × 4 RX 只告诉你最多有 12 种组合，不能确定它们在空间怎样排列。更换为 IWR1843BOOST 或其他板卡时，应从对应板卡的天线布局建立位置表，重新选择水平/俯仰通道并校准。上游取前 8 通道的写法不能仅因使用 IWR1843 就视为已验证正确。

先从硬件资料得到每个虚拟阵元的位置 $r_p$，再为每个候选角度 θ 计算它应有的相位。以一维坐标、同一符号约定为例：

\[
a_p(\theta)=e^{j2\pi r_p\sin\theta/\lambda},\qquad
P(\theta)=\left|\sum_p a_p^*(\theta)z_p\right|^2.
\]

这就是扫描波束形成：对一个角度假设做相位对齐，然后相加。它不要求位置等间隔，但位置、通道顺序与幅相校准仍然必须正确。二维阵列应使用方向向量与阵元位置向量的内积。

```python
# positions_m 与 z 一一对应；theta_grid 的单位为弧度
steering = np.exp(1j*2*np.pi/wavelength * positions_m[:,None] * np.sin(theta_grid)[None,:])
power = np.abs(steering.conj().T @ z)**2
```

```matlab
steering = exp(1j*2*pi/wavelength * positionsM(:)*sin(thetaGrid(:).'));
power = abs(steering' * z(:)).^2;  % 此处需要共轭转置
```

幅相校准可以用已知方向反射器估计各通道的复增益 $g_p$，在波束形成前用 `z/g` 做逐元素校正。估计时必须先扣除已知方向应有的几何相位；不能把真实的空间相位也当误差消掉。

## 5. 项目目前实际算了什么

```python linenums="271"
def run_angle_fft_strict(speed_profile: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    selected = speed_profile[:, :, cfg.angle_channels]
    # Strict MATLAB parity: angle FFT consumes the configured channel slice directly.
    return np.fft.fftshift(np.fft.fft(selected, n=cfg.angle_bin, axis=2), axes=2)
```

源文件：`project/src/iwr1443_adc_utils.py`，函数 `run_angle_fft_strict`。

默认选前 8 个通道，补零到 180 点。可前一步只算了前 4 个通道的 Doppler，选出的后 4 个已经是零。另外还没有确认阵元位置表、通道校准和运动补偿，所以当前结果应按空间 FFT 格来读。

<figure><img src="../assets/figures/range_angle_heatmap_strict.png" alt="距离与空间 FFT 格的二维热图"><figcaption>横轴看作有符号空间 FFT 格，纵轴是代码标注的距离。先观察重复的距离条纹，再观察横向分布。它同时受前端数据排列和零通道影响，还不能读出可信目标角度。</figcaption></figure>

## 检查点

试着回答：为什么 `q=45` 对应 30°；为什么 8 点补成 180 点不会变出 180 个天线；为什么运动补偿要在比较天线相位之前完成。下一章：[从距离处理处分出另一条路线，观察微位移](phase.md)。
