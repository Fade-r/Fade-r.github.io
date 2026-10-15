# 目标检测

距离—多普勒频谱中的峰可能来自目标，也可能来自噪声、静态背景或旁瓣。目标检测的任务是根据频谱和背景水平，选出需要进一步分析的位置。

## 幅度与功率

!!! formula-recap "距离—多普勒结果"

    [速度测量](../processing/doppler.md)的输出为 $D[k,\ell,p]$，对应 `doppler_cube`。$k$、$\ell$、$p$ 分别表示距离格、速度格和通道。每个元素都是复数，可以写成 $X=I+jQ=Ae^{j\phi}$。

FFT 输出是复数 $X$，常用的幅度和功率分别为：

\[
A=|X|,\qquad P=|X|^2.
\]

这里 $P=I^2+Q^2$ 是与功率成比例的数值。若采用幅度分贝，计算 $20\log_{10}(A/A_{\mathrm{ref}})$；采用功率分贝，计算 $10\log_{10}(P/P_{\mathrm{ref}})$。当 $P_{\mathrm{ref}}=A_{\mathrm{ref}}^2$ 时，两式相同，因为 $\log_{10}(A^2/A_{\mathrm{ref}}^2)=2\log_{10}(A/A_{\mathrm{ref}})$。dBm 专指相对于 1 mW 的物理功率；未经接收增益等标定的 FFT 数值，应写相对 dB，并说明参考值。

对多个通道进行非相干积累，可以将各通道功率相加：

```python
power_map = np.sum(np.abs(doppler_cube)**2, axis=2)
```

```matlab
powerMap = sum(abs(dopplerCube).^2,3);
```

`power_map` 的两个轴是距离和速度，计算的是 $P[k,\ell]=\sum_p|D[k,\ell,p]|^2$。这称为非相干积累，因为各通道先取模平方再相加，不要求它们相位一致。这样能得到检测位置，但取模已消去相位、求和又合并了通道；测角所需的通道间相位差必须从保留的 `doppler_cube` 取出。

## 固定阈值

最简单的检测方法是判断某个频谱格的功率是否大于阈值：

\[
P[k]>\eta.
\]

如果噪声水平随时间或位置变化，固定阈值会出现漏检或过多误报。CFAR（恒虚警率检测）使用邻近频谱格估计背景，再据此计算阈值。

## CA-CFAR

CA-CFAR 使用训练格的平均功率估计背景。待检测格称为 CUT；紧邻 CUT 的保护格不参与估计，以免把目标主瓣当成噪声。

例如训练格在两侧各取 2 个，中间留 1 个保护格：

```text
训练  训练  保护  CUT  保护  训练  训练
```

训练格总数为 $N$，背景估计为：

\[
\widehat P_n=\frac1N\sum_{i=1}^N P_i.
\]

阈值为 $\eta=\alpha\widehat P_n$。$\alpha$ 决定阈值比背景高多少；希望误报更少，就要用更大的 $\alpha$。若各训练格及 CUT 都是相互独立、同分布的指数噪声功率，则：

\[
P_{\mathrm{FA}}=(1+\alpha/N)^{-N}.
\]

对等式两边取 $-1/N$ 次幂，再移项，得到：

\[
\alpha=N\left(P_{\mathrm{FA}}^{-1/N}-1\right).
\]

这里的 $P_{\mathrm{FA}}$ 表示“只有噪声时，一个格超过阈值”的概率。例如 $P_{\mathrm{FA}}=0.001$ 意味着大量同类噪声格平均每 1000 次判决约有 1 次误报，有限数据的实际次数会波动。

一种常用的噪声模型是：I、Q 分别服从均值为零、方差相同的高斯分布，且彼此独立，合起来称为圆对称复高斯噪声。它的模平方 $I^2+Q^2$ 服从指数分布。多个独立、同等噪声水平通道的功率相加后，得到的是这些指数变量之和，服从 Gamma 分布，不再满足这里的单通道公式；加窗也可能使邻近格相关。

因此，下面的阈值系数先用于独立、单通道噪声模型；用于前述多通道功率图时，应按积累后的分布重新计算系数，或用纯背景数据检验并校准实际虚警率。

### 虚警概率公式的推导

!!! formula-recap "超过随机阈值的概率"

    \[
    \eta=\frac{\alpha}{N}\sum_{i=1}^{N}P_i,\qquad
    P_{\mathrm{FA}}=\Pr(P_{\mathrm{CUT}}>\eta\mid\text{只有噪声}).
    \]

    $N$ 是训练格总数，$P_i$ 是训练格功率。$\Pr$ 表示概率；下面的 $\mathbb E$ 表示按各种可能取值的概率求平均。先固定训练格求概率，再对训练格取平均。

设噪声功率的均值为 $\mu$，单个训练格 $P_i$ 的概率密度为 $p(u)=\mu^{-1}e^{-u/\mu}$，$u\ge0$。指数分布的尾概率为：

\[
\Pr(P_{\mathrm{CUT}}>h)
=\int_h^\infty\frac1\mu e^{-u/\mu}\,du
=e^{-h/\mu}.
\]

给定训练格功率后，阈值 $h=\alpha\sum_iP_i/N$ 已确定。再对训练格的随机取值求平均：

\[
\begin{aligned}
P_{\mathrm{FA}}
&=\mathbb E\left[\exp\left(-\frac{\alpha}{N\mu}\sum_{i=1}^N P_i\right)\right]\\
&=\prod_{i=1}^N\mathbb E\left[e^{-\alpha P_i/(N\mu)}\right].
\end{aligned}
\]

第二步利用了训练格相互独立。每一项期望都是同一个积分：

\[
\begin{aligned}
\mathbb E\left[e^{-\alpha P_i/(N\mu)}\right]
&=\int_0^\infty e^{-\alpha u/(N\mu)}\frac1\mu e^{-u/\mu}\,du\\
&=\frac1\mu\int_0^\infty
e^{-(1+\alpha/N)u/\mu}\,du\\
&=\frac{1}{1+\alpha/N}.
\end{aligned}
\]

$N$ 项相乘，即得到 $(1+\alpha/N)^{-N}$。例如 $N=4,\alpha=4$ 时，虚警概率为 $2^{-4}=1/16$。这个结论要求 CUT 与训练格也相互独立。

## 一个小例子

两侧共 4 个训练格，功率均为 1，CUT 功率为 8。为了便于计算，取 $\alpha=4$，阈值就是 4，所以检测结果为真。

### Python

```python
import numpy as np

power = np.array([1, 1, 2, 8, 2, 1, 1], dtype=float)
training = power[[0, 1, 5, 6]]
threshold = 4 * training.mean()
print(threshold, power[3] > threshold)
```

### MATLAB

```matlab
power = [1 1 2 8 2 1 1];
training = power([1 2 6 7]);
threshold = 4*mean(training);
disp(threshold);
disp(power(4) > threshold);
```

输出阈值为 4，检测结果为真。相邻功率为 2 的两个格是保护格，不参与背景计算。

## 一维 CA-CFAR 实现

以下函数的输入是线性功率，`train` 表示每侧训练格数量，`guard` 表示每侧保护格数量。边缘没有足够训练格，阈值保留为 NaN。

### Python

```python
import numpy as np

def ca_cfar(power, train=8, guard=2, pfa=1e-3):
    power = np.asarray(power, dtype=float)
    threshold = np.full(power.size, np.nan)
    count = 2*train
    alpha = count*(pfa**(-1/count)-1)
    margin = train+guard
    for k in range(margin, power.size-margin):
        left = power[k-guard-train:k-guard]
        right = power[k+guard+1:k+guard+train+1]
        noise = (left.sum()+right.sum())/count
        threshold[k] = alpha*noise
    detected = np.isfinite(threshold) & (power > threshold)
    return detected, threshold
```

### MATLAB

```matlab
function [detected, threshold] = ca_cfar(power, train, guard, pfa)
power = double(power(:));
threshold = nan(size(power));
count = 2*train;
alpha = count*(pfa^(-1/count)-1);
margin = train+guard;
for k = 1+margin:numel(power)-margin
    left = power(k-guard-train:k-guard-1);
    right = power(k+guard+1:k+guard+train);
    noise = (sum(left)+sum(right))/count;
    threshold(k) = alpha*noise;
end
detected = isfinite(threshold) & power > threshold;
end
```

MATLAB 版本可保存为 `ca_cfar.m`。两种实现的切片终点不同：Python 不包含右端点，MATLAB 包含。

## 静态杂波

墙壁、地面等静止物体常在零多普勒附近形成强回波。若研究目标是运动物体，可以在慢时间维减去复数均值：

```python
moving = range_cube - range_cube.mean(axis=1, keepdims=True)
```

```matlab
moving = rangeCube - mean(rangeCube,2);
```

对固定距离格和通道，设序列为 $u[m]$，均值为 $\bar u=N_c^{-1}\sum_m u[m]$。减均值后的零频 DFT 值为 $\sum_m(u[m]-\bar u)=0$，所以它能去掉不随轮次变化的分量。静止目标也属于这种分量；若要保留静止反射器或分析微动，就不能不加区分地去掉它。后续加窗会改变各点权重，此时零频结果不一定严格为零。

## 检测格与目标数

一个目标的主瓣可能覆盖多个相邻格，因此检出三个格并不等于有三个目标。检测后通常还需要选局部峰值、合并邻近检测，并在时间上关联目标。

本页的一维 CFAR 沿一条频谱取两侧训练格。二维 CFAR 则在距离—多普勒平面围绕 CUT 取训练区域，并留出保护区域。生成点云还需把相邻检出格合并为目标，为每个目标估计角度，再将距离和方向换成空间坐标。

原理参考：H. Rohling, “Radar CFAR Thresholding in Clutter and Multiple Target Situations,” IEEE TAES, 1983, [doi:10.1109/TAES.1983.309350](https://doi.org/10.1109/TAES.1983.309350)。
