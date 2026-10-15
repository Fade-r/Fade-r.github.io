# 从谱峰到目标：检测、杂波和验证

FFT 给你的是频谱，还没有回答“哪些格里存在目标”。最强峰可能是墙面、直流泄漏或干扰；一个目标的主瓣也可能覆盖多个格。这一章补上目标检测的基本思路，方便你理解当前项目还缺哪一步。

## 1. 幅度、功率和 dB 不要混用

复频谱 X 的幅度为 $|X|$，线性功率量为 $|X|^2$。相对幅度的 dB 用 $20\log_{10}(|X|/A_0)$；相对功率的 dB 用 $10\log_{10}(P/P_0)$。这两个表达在参考值匹配时等价。它们都不会自动给出瓦特或 dBm，后者需要接收链路标定。

```python
power = np.abs(R)**2
relative_db = 10*np.log10(np.maximum(power/power.max(), 1e-12))
```

```matlab
power = abs(R).^2;
relativeDB = 10*log10(max(power/max(power(:)),1e-12));
```

## 2. 为什么有时要去掉静态杂波

在同一距离格，完全静止的回波通常集中在零多普勒附近。沿轮次减去复数均值，可抑制这部分回波：

\[
X'_r[k,m,p]=X_r[k,m,p]-\frac{1}{N_c}\sum_{m'=0}^{N_c-1}X_r[k,m',p].
\]

```python
R_clean = R - R.mean(axis=1, keepdims=True)
```

```matlab
Rclean = R - mean(R,2);
```

这会同时削弱静止和很慢的目标。若要观察呼吸等微动，或者保留静态目标位置，不能不加判断地使用它。应先确定要估计什么，再选择杂波处理方法。

## 3. CFAR 怎样让阈值跟着背景变化

固定阈值很容易受环境影响。CA-CFAR（单元平均恒虚警检测）在每个待检测格周围选一组训练格，用它们估计局部噪声功率，再乘一个系数作为阈值。待检测格左右留出保护格，避免把目标主瓣也算进噪声。

```text
左侧训练格 | 保护格 | 待检测格 | 保护格 | 右侧训练格
   估计背景           与阈值比较           估计背景
```

若训练格和待检测格的功率独立且服从同均值指数分布，训练格共 M 个：

\[
\widehat P_n=\frac1M\sum_{i=1}^{M}P_i,\quad
\alpha=M(P_{\mathrm{FA}}^{-1/M}-1),\quad
P_{\mathrm{CUT}}>\alpha\widehat P_n.
\]

其中 $P_{\mathrm{FA}}$ 是模型下的目标虚警概率。关系来自 $P_{\mathrm{FA}}=(1+\alpha/M)^{-M}$。实际加窗、相邻格相关、多通道平均和非均匀杂波都可能改变分布，所以这个参数不是实测虚警率的保证。

### Python 教学实现

```python
def ca_cfar(power, training=8, guard=2, pfa=1e-3):
    count = 2 * training
    alpha = count * (pfa ** (-1 / count) - 1)
    threshold = np.full(power.shape, np.nan, dtype=float)
    detected = np.zeros(power.shape, dtype=bool)
    for k in range(training + guard, len(power) - training - guard):
        left = power[k - guard - training:k - guard]
        right = power[k + guard + 1:k + guard + training + 1]
        noise = np.mean(np.concatenate((left, right)))
        threshold[k] = alpha * noise
        detected[k] = power[k] > threshold[k]
    return detected, threshold
```

### MATLAB 教学实现

```matlab
function [detected, threshold] = ca_cfar(power, training, guard, pfa)
    count = 2*training;
    alpha = count*(pfa^(-1/count)-1);
    threshold = nan(size(power));
    detected = false(size(power));
    for k = training+guard+1:numel(power)-training-guard
        left = power(k-guard-training:k-guard-1);
        right = power(k+guard+1:k+guard+training);
        noise = mean([left(:); right(:)]);
        threshold(k) = alpha*noise;
        detected(k) = power(k) > threshold(k);
    end
end
```

两份实现都跳过边缘，因为那里没有足够的训练格。未检查的阈值为 NaN，不应把它当成“确认无目标”。这里以一维距离功率作教学练习；实际常在距离—多普勒平面设计二维检测器，并处理边缘、邻近强目标和非均匀杂波。

## 4. 检出三个格，不一定是三个目标

完整模拟练习只有一个目标，却会检出 13、14、15 三个相邻距离格，因为加窗后的主瓣有宽度。可先把连在一起的检测格归为一组，再在组内找峰或估计中心。多个真实目标距离过近时，这一步还可能把它们混在一起，因此要结合分辨能力判断。

跨帧处理还要解决“这一帧的目标是不是上一帧那个”的关联问题。固定一个 bin 并不等于完成跟踪；目标移动到相邻 bin 后，继续读原来的 bin 会混入另一种相位变化。正式的目标跟踪、滤波与多目标关联超出当前项目的已实现功能。

## 检查点

你应能区分：频谱计算、超过阈值、合并检测格、跨帧关联，是四个不同步骤。当前生产代码尚无 CFAR；本章代码只用于学习。下一章：[运行完整练习并按已知答案逐步核验](end-to-end.md)。
