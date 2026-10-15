# 先看懂一帧数据

雷达不断发出扫频信号：发射频率在一小段时间内逐渐升高，这一段叫 **chirp（一次扫频）**。接收机把回波与本机信号混频，再由 ADC 采样。文件保存的是这些采样值，不是直接测得的距离。

## 三个方向，三种比较

先看项目交给 FFT 的一帧数据：

```python
frame[sample, loop, channel]   # shape = (256, 128, 12)
```

方括号里的三个位置分别回答：这次扫频中的第几个点、这一帧的第几轮、哪一组发射与接收天线。Python 从 0 编号，所以第一个点写作 `sample=0`。

<div class="axis-lessons">
<section><h3>沿采样点读 → 距离</h3><code>frame[:, 0, 0]</code><p>固定第 0 轮、第 0 通道，把 256 个点按时间排开。FFT 找出这段回波里的拍频，再换算成距离。</p><p><strong>代码里选 axis=0。</strong>冒号表示“这一维全部取出”。</p></section>
<section><h3>沿重复观测读 → 速度</h3><code>range_profile[k, :, 0]</code><p>先做完距离 FFT，再固定第 k 个距离格和第 0 通道。比较 128 轮观测，看同一处回波的相位如何变化。</p><p><strong>代码里选 axis=1。</strong>这里不再比较原始 ADC 点。</p></section>
<section><h3>沿通道读 → 方向</h3><code>speed_profile[k, l, :]</code><p>距离、速度都固定后，取各通道的复数值。天线处在不同位置，同一方向的回波会留下有规律的相位差。</p><p><strong>代码里选 axis=2。</strong>前提是通道顺序与实际阵列一致。</p></section>
</div>

三个 FFT 不会自动知道哪个方向是距离或速度。是你把数据按物理顺序排好，再通过 `axis` 告诉它沿哪一维计算。

## 12 个通道是怎么来的

代码设置了 3 个发射天线（TX）、4 个接收天线（RX），共 12 种发射—接收组合。这样的组合叫虚拟通道。例如，TX1 发射、RX2 接收，就是其中一个通道。

如果三路 TX 依次轮流发射，一轮有 3 次实际扫频；128 轮就是 384 次扫频。对某一个虚拟通道而言，仍然只有 128 次观测。代码里的 `chirps=128` 在这个解释下指每通道的重复次数，不是整帧所有 TX 的发射总次数。

这解释了为什么“12 个通道”不等于“12 根同时采样、等间距排开的天线”。[速度时间间隔](../processing/doppler.md)和[角度估计](../processing/angle.md)都要用到这个区别。

## 同一批数为什么有两种 shape

存储所有帧时，代码使用：

```text
adc_cube[帧, 通道, 轮次, 采样点] = (100, 12, 128, 256)
```

处理一帧时，为了对照 MATLAB，又换成：

```text
frame[采样点, 轮次, 通道] = (256, 128, 12)
```

`frame_to_matlab_view` 用 `transpose(2, 1, 0)` 调换单帧的三个轴，数据值本身不变。之后的 `axis=0` 才对应采样点。把另一个形状的数组直接送进去，即使 FFT 能运行，物理含义也可能已经错了。

## 接下来怎样读

1. [复数、采样和 FFT](../foundations/signal-and-fft.md)：用八个能手算的点理解频谱。
2. [参数页](parameters-and-shapes.md)和[I/Q 页](../data/adc-iq-layout.md)：算清数据量，边理解排列规则边用两种语言还原一帧复数。
3. [距离](../processing/range.md)、[速度](../processing/doppler.md)、[角度](../processing/angle.md)：每个步骤在本页完成推导、编程和输出检查。
4. [相位页](../processing/phase.md)和[目标检测](../practice/detection.md)：同样边推公式边写代码，学习选择目标、保留相位、判断结果。
5. [完整练习](../practice/end-to-end.md)：把已经学过的代码连起来，再主动改变参数，检查你能否预测输出。

遇到语法忘记时查[MATLAB/Python 速查表](../foundations/arrays-and-languages.md)；寻找原文件位置时查[函数索引](../code/code-map.md)。这两页是辅助资料，不是学习主线中的必经步骤。
