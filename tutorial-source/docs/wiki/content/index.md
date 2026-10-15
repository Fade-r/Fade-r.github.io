# 毫米波雷达教程

雷达是一种利用电磁波探测物体的设备。它通过天线发射信号，再接收物体反射回来的信号。接收到的反射信号称为**回波**。

回波与发射信号并不完全相同。电磁波传播需要时间，物体运动会改变回波的频率和相位，不同位置的天线接收到的回波也有差别。雷达利用这些差别测量目标的距离、速度和方向。

## 毫米波雷达是什么

毫米波是波长约为 1～10 mm 的电磁波。例如，77 GHz 电磁波的波长约为 3.9 mm。使用这类电磁波工作的雷达称为毫米波雷达，常用于车辆感知、人员检测和微小运动测量。

IWR1443 和 IWR1843 是 TI 的毫米波雷达芯片，均工作在 76～81 GHz 频段。两者的测距、测速原理相同，但数据接口和开发板天线布局需要分别配置。[^1][^2]

## FMCW 雷达是什么

FMCW 是“调频连续波”的缩写。它在一段时间内连续发射信号，同时逐渐改变发射频率。这种频率随时间变化的信号称为**扫频信号**，一次扫频通常称为一个 **chirp**。

物体越远，回波返回得越晚。雷达收到回波时，发射频率已经发生变化。比较两者的频率差，就能计算距离。重复发射多个 chirp，可以进一步测量速度；使用多个天线，可以估计方向。

## 教程内容

内容按信号的产生、接收、采样和处理顺序编排。各处理步骤分别提供 MATLAB 和 Python 示例。

| 部分 | 内容 |
| --- | --- |
| 发射与接收 | [发射信号](foundations/transmit.md)、[回波与混频](foundations/echo-and-mixing.md) |
| 数据采集 | [I/Q 与采样](foundations/sampling.md)、[雷达与采集卡](data/capture.md)、[数据读取](data/adc-iq-layout.md) |
| 信号处理 | [FFT](foundations/signal-and-fft.md)、[距离](processing/range.md)、[速度](processing/doppler.md)、[检测](practice/detection.md)、[角度](processing/angle.md)、[微位移](processing/phase.md) |
| 编程与实验 | [完整示例](practice/end-to-end.md)、[项目代码分析](code/code-map.md)、[实验验证](audit/validation-roadmap.md) |

编程示例使用数组、循环和函数；数学部分涉及三角函数、复数和求和。复数、频谱和数组维度会在使用时介绍。

[^1]: Texas Instruments. [IWR1443 数据手册](https://www.ti.com/lit/ds/symlink/iwr1443.pdf).
[^2]: Texas Instruments. [IWR1843 数据手册](https://www.ti.com/lit/ds/symlink/iwr1843.pdf).
