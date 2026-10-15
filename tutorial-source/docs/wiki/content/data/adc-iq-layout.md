# ADC 数据读取

ADC 采样经过接口传输并保存后，需要按约定的存储顺序读回 I、Q，再排列为 `[采样点,轮次,通道]` 数组。本章分别说明读取整数、I/Q 配对和数组重排。

## 读取 16 位整数

以下示例使用纯 ADC 文件、小端字节序、有符号 16 位存储。将待处理文件保存为 `capture.bin`，或在代码中改为实际路径。

### Python

```python
import numpy as np

raw = np.fromfile('capture.bin', dtype='<i2')
print(raw.size)
```

`'<i2'` 中，`<` 表示小端，`i` 表示有符号整数，`2` 表示每个整数占 2 字节。

### MATLAB

```matlab
fid = fopen('capture.bin','r','ieee-le');
assert(fid ~= -1, 'Cannot open ADC file');
raw = fread(fid,Inf,'int16=>double');
fclose(fid);
disp(numel(raw));
```

`fopen` 打开文件，`fread` 读出全部整数并转换成浮点数，`fclose` 关闭文件。`Inf` 表示读到文件结束。

## IWR1443 四路接收的 I/Q 配对

TI 的 SWRA581B 给出了 xWR14xx 四路 RX、复数采样、I-first 的示例格式：同一采样时刻先排列四路 I，再排列四路 Q。[^1]

```text
I_RX1  I_RX2  I_RX3  I_RX4  Q_RX1  Q_RX2  Q_RX3  Q_RX4
```

例如八个数 `[1,2,3,4,11,12,13,14]` 对应四个复数：

```text
1+11j   2+12j   3+13j   4+14j
```

### Python

```python
import numpy as np

raw_example = np.array([1,2,3,4,11,12,13,14])
words = raw_example.astype(float).reshape(-1, 8)
rx_samples = words[:, :4] + 1j * words[:, 4:]
print(rx_samples)
```

`reshape(-1,8)` 每 8 个数组成一行；`:4` 取前四列，`4:` 取后四列。输出每行对应一个采样时刻，每列对应一个 RX。

### MATLAB

```matlab
rawExample = [1 2 3 4 11 12 13 14];
words = reshape(double(rawExample),8,[]);
rxSamples = words(1:4,:) + 1j*words(5:8,:);
disp(rxSamples);
```

MATLAB 按列填充数组，因此每列放一个八元组，输出每行对应一个 RX。这时两种语言的中间数组互为转置，下一步会统一维度。

## 排列一帧数据

假设每个 chirp 采 $N_s=256$ 点，3 路 TX 按 TX1、TX2、TX3 轮发，共 $N_c=64$ 轮，4 路 RX 都启用。代码中的点数、轮次和通道数应与文件对应的采集设置一致。

文件中的变化顺序为：同一采样时刻的 RX → 下一个采样时刻 → 下一路 TX 的 chirp → 下一轮。虚拟通道按 TX1-RX1～RX4、TX2-RX1～RX4、TX3-RX1～RX4 排列。

### Python

```python
ns, nc, ntx, nrx = 256, 64, 3, 4
per_frame = ns * nc * ntx * nrx * 2
raw_frame = raw[:per_frame]
assert raw_frame.size == per_frame

words = raw_frame.astype(float).reshape(-1, 8)
rx_samples = words[:, :4] + 1j*words[:, 4:]
physical = rx_samples.reshape(nc, ntx, ns, nrx)
frame = physical.transpose(2, 0, 1, 3).reshape(ns, nc, ntx*nrx)
assert frame.shape == (256, 64, 12)
```

`physical` 的四个轴是轮次、TX、采样点、RX。`transpose(2,0,1,3)` 将采样点移到最前；最后一个 `reshape` 合并 TX 和 RX，形成虚拟通道。

### MATLAB

```matlab
ns = 256; nc = 64; ntx = 3; nrx = 4;
perFrame = ns*nc*ntx*nrx*2;
assert(numel(raw) >= perFrame);
rawFrame = double(raw(1:perFrame));

words = reshape(rawFrame,8,[]);
rxSamples = words(1:4,:) + 1j*words(5:8,:);
physical = reshape(rxSamples,nrx,ns,ntx,nc);
frame = reshape(permute(physical,[2 4 1 3]),ns,nc,nrx*ntx);
assert(isequal(size(frame),[256 64 12]));
```

`permute` 交换维度，作用相当于 NumPy 的多维 `transpose`。这里保留 RX 在虚拟通道编号中变化最快，两种语言最后得到相同的采样点归属。

### 每个元素去了哪里

下面将每个 chirp 缩小到 2 个采样点、每帧缩小到 2 轮，仍保留 3 TX、4 RX。原始整数用 `1,2,…,96` 标记位置，不代表真实回波。选择一个元素，可以同时看到它的 I/Q 来源和最终矩阵位置。

<section class="signal-lab" data-lab="layout" aria-label="I/Q 与数组索引演示" hidden>
  <div class="lab-controls">
    <label>采样点 n <select data-control="n"><option value="0">0</option><option value="1">1</option></select></label>
    <label>轮次 m <select data-control="m"><option value="0">0</option><option value="1">1</option></select></label>
    <label>发射 TX <select data-control="tx"><option value="0">TX1</option><option value="1">TX2</option><option value="2">TX3</option></select></label>
    <label>接收 RX <select data-control="rx"><option value="0">RX1</option><option value="1">RX2</option><option value="2">RX3</option><option value="3">RX4</option></select></label>
  </div>
  <p>同一采样时刻的八元组（先 I，后 Q）：</p>
  <div class="lab-words" data-view="words"></div>
  <p data-view="slice-title"></p>
  <div class="lab-matrix" data-view="matrix"></div>
  <p class="lab-result" data-view="result" aria-live="polite"></p>
  <p data-view="indices"></p>
</section>

用从 0 开始的索引表示，设 TX 编号为 $a$、RX 编号为 $r$。到达第 $m$ 轮、第 $a$ 路 TX 之前，已经经过 $mN_{\mathrm{TX}}+a$ 个 chirp。每个 chirp 有 $N_s$ 个采样时刻，所以当前八元组的编号是：

\[
g=(mN_{\mathrm{TX}}+a)N_s+n.
\]

每组含 8 个整数，因此 I 与 Q 在原始序列中的位置分别是 $8g+r$、$8g+4+r$。合并 TX/RX 后，虚拟通道编号为 $p=4a+r$：

\[
x[n,m,4a+r]=\mathrm{raw}[8g+r]+j\,\mathrm{raw}[8g+4+r].
\]

例如选择 $n=1,m=1,\mathrm{TX2},\mathrm{RX3}$，则 $a=1,r=2$：

\[
g=(1\times3+1)\times2+1=9,\qquad p=4\times1+2=6.
\]

I、Q 的零起始位置为 74 和 78，对应标记值 75 和 79，所以 Python 的 `frame[1,1,6]` 和 MATLAB 的 `frame(2,2,7)` 都应为 `75+79j`。`reshape` 与 `transpose/permute` 的目的就是保留这个对应关系，而不是只凑出正确的尺寸。

## IWR1843 格式

IWR1843 使用两条 LVDS 数据通道。所参考的 IWR1843 教程使用 `[I0,I1,Q0,Q1]` 四元组：

```python
words = raw.astype(float).reshape(-1, 4)
z = (words[:, :2] + 1j*words[:, 2:]).reshape(-1)
```

```matlab
words = reshape(double(raw),4,[]);
z = reshape(words(1:2,:) + 1j*words(3:4,:),[],1);
```

这是该参考代码采用的格式，不能仅根据“两条 LVDS”就确定任意 IWR1843 文件都符合它。实际还需核对采集软件版本、ADC 模式、I/Q 顺序和通道交织方式。SWRA581B 的旧版没有直接覆盖 IWR1843，应结合该设备的采集说明使用。

当前项目也沿用了四元组配对，尚未根据 IWR1443 的完整采集记录确认。原函数及其重排方式放在[项目代码分析](../code/code-map.md)，不作为本章四路 RX 示例的正确性依据。

## 检查读取结果

先用人工构造的小数组检查每个值的位置，再用已知距离的强反射目标检查距离谱。单纯得到 `(256,64,12)` 的形状并不能证明重排正确：不同排列都可能有相同尺寸。

更换采集参数时，需要同时修改每帧长度、I/Q 配对和 TX/RX 重排规则。数据值、所属天线和观测时刻三者必须对应。

[^1]: TI. [ADC Raw Data Capture，SWRA581B](https://www.ti.com/lit/an/swra581b/swra581b.pdf)，§5 图 9、§9.1。参考代码来源见[来源索引](../reference/sources.md)。
