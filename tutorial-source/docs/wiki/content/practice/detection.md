# 目标检测

距离—多普勒频谱中的峰可能来自目标，也可能来自噪声、静态背景或旁瓣。目标检测的任务是根据频谱和背景水平，选出需要进一步分析的位置。

## 幅度与功率

FFT 输出是复数 $X$，常用的幅度和功率分别为：

\[
A=|X|,\qquad P=|X|^2.
\]

如果采用幅度分贝，计算 $20\log_{10}(A/A_{\mathrm{ref}})$；采用功率分贝，计算 $10\log_{10}(P/P_{\mathrm{ref}})$。参考值必须说明，未标定的 FFT 输出不能直接标成 dBm。

对多个通道进行非相干积累，可以将各通道功率相加：

```python
power_map = np.sum(np.abs(doppler_cube)**2, axis=2)
```

```matlab
powerMap = sum(abs(dopplerCube).^2,3);
```

`power_map` 的两个轴是距离和速度。它用于检测位置；测角仍要从原来的复数 `doppler_cube` 取各通道数据，不能用功率图代替。

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

阈值为 $\eta=\alpha\widehat P_n$。当各训练格为独立、同分布的指数噪声功率，且 CUT 只有同类噪声时：

\[
P_{\mathrm{FA}}=(1+\alpha/N)^{-N}.
\]

对等式两边取 $-1/N$ 次幂，再移项，得到：

\[
\alpha=N\left(P_{\mathrm{FA}}^{-1/N}-1\right).
\]

这里的 $P_{\mathrm{FA}}$ 是设定的单格虚警概率，不是某次有限数据上一定出现的误报比例。加窗、杂波和多通道积累会改变统计条件，需要相应调整检测器。

### 虚警概率公式的推导

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

减均值会压低零多普勒分量，也会削弱静止目标。它是针对测量目的的选择，不是每次处理都必须加入的步骤。

## 检测格与目标数

一个目标的主瓣可能覆盖多个相邻格，因此检出三个格并不等于有三个目标。检测后通常还需要选局部峰值、合并邻近检测，并在时间上关联目标。

实际距离—多普勒图常使用二维 CFAR。这里的一维实现用于说明训练格、保护格和阈值计算，不把它直接当作完整点云算法。

原理参考：H. Rohling, “Radar CFAR Thresholding in Clutter and Multiple Target Situations,” IEEE TAES, 1983, [doi:10.1109/TAES.1983.309350](https://doi.org/10.1109/TAES.1983.309350)。
