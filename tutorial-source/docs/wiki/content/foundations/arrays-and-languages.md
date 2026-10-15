# MATLAB/Python 数组操作

两种语言均可用三维数组保存一帧雷达数据。本页使用 `采样点 × 轮次 × 通道` 的维度顺序，并以原程序中的 `256 × 128 × 12` 为例。

## 数组索引

| 要取什么 | Python / NumPy | MATLAB |
| --- | --- | --- |
| 数组尺寸 | `frame.shape` | `size(frame)` |
| 第一轮、第一通道的所有点 | `frame[:,0,0]` | `frame(:,1,1)` |
| 零起始距离格 14 的所有轮次 | `R[14,:,0]` | `R(15,:,1)` |
| 前四个通道 | `R[:,:,:4]` | `R(:,:,1:4)` |
| 沿采样点做 FFT | `np.fft.fft(frame, axis=0)` | `fft(frame,[],1)` |
| 沿轮次做 FFT | `np.fft.fft(R, axis=1)` | `fft(R,[],2)` |
| 沿通道做 FFT | `np.fft.fft(D, axis=2)` | `fft(D,[],3)` |

Python 的索引和轴从 0 开始；MATLAB 从 1 开始。Python 切片右端不包含在结果内，`0:4` 取 0、1、2、3。物理公式中的 bin 编号通常从 0 开始，所以 MATLAB 找到峰后要先减 1，再用距离公式。

## reshape 和 transpose 分别做什么

`reshape` 把一个线性序列填进新形状；`transpose` / `permute` 调换已有数组的轴。它们都不增加采样值，却可能改变你把某个值认作“哪个天线、哪个时刻”的方式。

MATLAB 按列填充。NumPy 默认按行填充，要复现 MATLAB 的 `reshape`，通常必须明确写 `order='F'`。不要仅凭结果尺寸一致就认为结果相同。

Python：

```python
import numpy as np
x = np.arange(1, 7)
print(x.reshape(2, 3))             # [[1,2,3], [4,5,6]]
print(x.reshape(2, 3, order='F'))  # [[1,3,5], [2,4,6]]
```

MATLAB：

```matlab
x = 1:6;
disp(reshape(x,2,3));             % [1 3 5; 2 4 6]
```

项目把一帧从 `[通道,轮次,采样点]` 换成 `[采样点,轮次,通道]`：

```python
frame = adc_cube[frame_index].transpose(2, 1, 0)
```

若 MATLAB 中已有同样的三维 `stored_frame`，对应写法是：

```matlab
frame = permute(stored_frame, [3 2 1]);
```

还有一个特别容易忽略的区别：NumPy `.T` 和 MATLAB `.'` 只转置；MATLAB `'` 是共轭转置，会把虚部符号反过来。处理 I/Q 数据时不能随意混用。

## 窗函数怎样乘到每一条信号上

要给每个通道、每轮的 256 个点乘同一个窗，让窗的形状成为 `[256,1,1]`。两个长度为 1 的维度会自动扩展到对应的轮次和通道；这就是广播或隐式扩展。

Python：

```python
w = np.hamming(256).reshape(256, 1, 1)
windowed = frame * w
assert windowed.shape == frame.shape
```

MATLAB（R2016b 及以上）：

```matlab
w = reshape(0.54-0.46*cos(2*pi*(0:255)/255),256,1,1);
windowed = frame .* w;
assert(isequal(size(windowed),size(frame)));
```

MATLAB 的 `.*` 表示逐元素相乘，`*` 是矩阵乘法；NumPy 普通数组的 `*` 已是逐元素相乘，矩阵乘法用 `@`。

## 尺寸、索引与数值检查

例如，未补零的距离 FFT 前后都应为 `[256,128,12]`，但第一轴的含义由采样点变成了距离格。还要查看每个通道的数值：下面将模平方沿前两个轴求和，得到各通道能量，可用来发现意外全零的通道。尺寸正确只说明数组能容纳这些值，无法证明数据来自正确的天线和时刻。

```python
assert frame.shape == (256, 128, 12)
assert np.isfinite(frame).all()
channel_energy = np.sum(np.abs(frame)**2, axis=(0,1))
```

```matlab
assert(isequal(size(frame),[256 128 12]));
assert(all(isfinite(frame(:))));
channel_energy = squeeze(sum(sum(abs(frame).^2,1),2));
```

这些操作在 [ADC 数据读取](../data/adc-iq-layout.md)中用于 I/Q 配对和帧重排。语言细节可查 [NumPy reshape](https://numpy.org/doc/stable/reference/generated/numpy.reshape.html) 和 [MATLAB permute](https://www.mathworks.com/help/matlab/ref/permute.html)。
