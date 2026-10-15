# 完整处理示例

这个示例生成一个已知距离、速度和方向的理想目标，再依次计算距离 FFT、多普勒 FFT、功率图和角度谱。输入和答案都已知，便于检查每一步的数组和坐标。

## 示例参数

| 参数 | 值 |
| --- | --- |
| 参考频率 | 77 GHz |
| 扫频斜率 | 30 MHz/µs |
| ADC 采样率、采样点数 | 8 MHz、256 点 |
| 同通道重复间隔、观测次数 | 1 ms、64 次 |
| 阵列 | 8 个半波长等间距通道 |
| 目标距离、方向 | 5 m、30° |
| 目标多普勒频率 | 125 Hz，对应约 0.244 m/s |

阵列是理想的一维均匀线阵，通道同时观测或已经完成运动补偿，不对应 IWR1443 或 IWR1843 的整块板卡布局。

## 构造采样信号

把距离、速度和空间相位相加：

\[
x[n,m,p]=
\exp\left\{j\left[
2\pi f_b\frac{n}{F_s}
+2\pi f_DmT_{\mathrm{slow}}
+\frac{2\pi pd\sin\theta}{\lambda}
\right]\right\}.
\]

三个索引分别表示：

- $n$：一次 chirp 内的采样点；
- $m$：同一通道的观测次数；
- $p$：按空间位置排列的阵元。

这是解调后采样数据的可分离近似模型。它忽略单次 chirp 内运动引起的拍频修正，也不模拟射频电路和网络传输。

### Python

```python
import numpy as np

ns, nc, channels = 256, 64, 8
fs, tslow = 8e6, 1e-3
fb, fd, theta = 1e6, 125.0, np.deg2rad(30)

n = np.arange(ns)[:, None, None]
m = np.arange(nc)[None, :, None]
p = np.arange(channels)[None, None, :]
frame = np.exp(1j*(2*np.pi*fb*n/fs
                  + 2*np.pi*fd*m*tslow
                  + np.pi*p*np.sin(theta)))
print(frame.shape)
```

### MATLAB

```matlab
ns = 256; nc = 64; channels = 8;
fs = 8e6; tslow = 1e-3;
fb = 1e6; fd = 125; theta = 30;

n = reshape(0:ns-1,[],1,1);
m = reshape(0:nc-1,1,[],1);
p = reshape(0:channels-1,1,1,[]);
frame = exp(1j*(2*pi*fb*n/fs+2*pi*fd*m*tslow+pi*p*sind(theta)));
disp(size(frame));
```

输出尺寸为 `256 × 64 × 8`。`n`、`m`、`p` 分别只在一个轴上变化，广播运算把三部分相位组合成三维数组。

## 运行完整程序

下载：[Python 程序](../assets/downloads/tutorial_pipeline.py) · [MATLAB 程序](../assets/downloads/tutorial_pipeline.m)。

Python 依赖 NumPy；MATLAB 使用基础函数和手写 Hamming 窗，不依赖 Signal Processing Toolbox。在保存文件的目录中运行：

```text
python tutorial_pipeline.py
```

MATLAB 中运行 `tutorial_pipeline`。

两个程序均使用合成数据，不需要采集文件。函数 `ca_cfar` 放在完整程序中；单独使用 MATLAB 版本时，可将其另存为同名文件。

## 各步结果

| 步骤 | 结果 |
| --- | --- |
| 构造数据 | `256 × 64 × 8` 个复数 |
| 距离 FFT | 峰在零起始第 32 格，对应 5 m |
| 多普勒 FFT | 峰在中心右侧第 8 格，对应 125 Hz |
| 速度换算 | 约 0.243506 m/s |
| 64 点空间 FFT | 峰在中心右侧第 16 格，对应 30° |
| 一维距离 CA-CFAR | 检出零起始第 31、32、33 格 |

Hamming 窗使距离主瓣覆盖相邻格，因此 CFAR 检出多个格。示例只有一个目标，它们不能被计作三个目标。

程序在距离—速度功率图上选择最强点来演示测角。这利用了“只有一个目标”的已知条件，不等同于多目标检测算法。

## 修改参数

将目标距离由 5 m 改为 10 m，拍频应由 1 MHz 变为 2 MHz，距离峰由第 32 格移到第 64 格。

保持输入不变，仅把速度轴换算使用的 `tslow` 缩小一半，估计速度会增大一倍。这可以检查程序是否混用了 ADC 采样率与慢时间间隔。

将目标方向由 30° 改为 −30°，空间谱峰应从中心右侧第 16 格移到左侧第 16 格。若只逆序排列通道，估计角度也会反号。

## 使用采集数据

真实数据替换的是本例中的 `frame`。替换前需要完成：

1. 按采集格式还原 I/Q，并确认采样点、轮次、TX/RX 的对应关系。
2. 将采样率、斜率和重复间隔替换为实际参数。
3. 按开发板位置选择阵列通道，校准幅相，并补偿 TDM 时间差。
4. 用已知距离、速度和方向的目标分别验证坐标换算。

完整程序还包含四路 RX 的数据排列测试、TDM 相位补偿测试和微位移测试。这些是独立的数值测试，不会把理想阵列误当作板卡实测数据。
