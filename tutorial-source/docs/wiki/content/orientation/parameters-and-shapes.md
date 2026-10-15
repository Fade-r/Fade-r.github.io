# 参数和数组尺寸

先把每个数对应到采集动作，再代入公式。以下是**当前代码设置**；还需要用实际采集配置核实这些设置。

!!! info "IWR1843 用户也从自己的采集参数代入"
    两种芯片都具备 3 TX、4 RX，实际启用数量和发射顺序由配置决定。256 点、128 轮、10 MHz、60 µs、100 µs 和 80 ms 都是本项目设置，不是任何一个型号固定不变的参数。迁移时重新计算每帧字节数、有效带宽、波长和同一 TX 的重复间隔。

## 一帧到底装了多少数据

每次扫频采 256 点，每个虚拟通道重复观察 128 次，共 3 × 4 = 12 个通道。每个采样点保存 I、Q 两个整数，每个整数占 2 字节。

\[
\text{每帧字节数}=256\times128\times12\times2\times2=1,572,864.
\]

文件大小是 157,286,400 字节，恰好是上述大小的 100 倍。这说明文件长度与这组配置相容；仅靠整除，还不能证明通道排列也正确。

| 处理到哪一步 | 数组尺寸 | 每一维表示什么 |
| --- | --- | --- |
| 读取一帧整数 | `(786432,)` | 一个长整数序列 |
| 组成复数 | `(393216,)` | I、Q 两个整数合成一个数 |
| 重排一帧 | `(256,128,12)` | 采样点、轮次、通道 |
| 距离 FFT 后 | `(256,128,12)` | 距离格、轮次、通道 |
| 多普勒 FFT 后 | `(256,128,12)` | 距离格、速度格、通道 |
| 角度 FFT 后 | `(256,128,180)` | 距离格、速度格、空间频率格 |

尺寸没变，不等于含义没变。例如距离 FFT 把 256 个时间采样点变成 256 个频率格；随后才把频率格换算成距离。角度 FFT 的 180 是人为设置的计算点数，不是采到了 180 个通道。

## 三个可以动手算的例子 { #hands-on }

下面只做理论计算，不加载实测数据。每个例子只改变一个量，图不会自动播放。先读“看哪里”，再拖动滑块或按按钮；结果和解释会一起更新。

<section class="teaching-demo" id="range-demo" aria-labelledby="range-demo-title">
<h3 id="range-demo-title">1. 目标变远，距离谱的峰往哪里走？</h3>
<p><strong>看哪里：</strong>下面标尺上的竖线表示理论峰的位置。这里沿用项目的 256 点距离 FFT，取正频率一侧的 0–64 格作示意。</p>
<label for="demo-range">目标距离：<output id="range-value" for="demo-range">5.0 m</output></label>
<input id="demo-range" type="range" min="1" max="10" step="0.5" value="5">
<div class="demo-buttons"><button type="button" data-range="5">比较：5 m</button><button type="button" data-range="10">比较：10 m</button></div>
<div class="bin-scale" role="img" aria-label="理论峰位于第 25.6 格"><div class="bin-marker" id="range-marker" style="left:40%"></div></div>
<div class="scale-labels"><span>第 0 格</span><span>第 32 格</span><span>第 64 格</span></div>
<p class="demo-result" id="range-result" aria-live="polite">5.0 m → 拍频 0.9994 MHz → 第 25.58 格附近。</p>
<p id="range-explanation">距离从 5 m 加倍到 10 m，回波延迟和拍频也约加倍，谱峰从第 25.6 格移到第 51.2 格附近。</p>
<p class="demo-equation">计算：拍频 f<sub>b</sub> = 2SR/c；格编号 k = f<sub>b</sub>N/F<sub>s</sub>。这里忽略速度项。实际 FFT 在整数格上取值，25.58 是理论位置，邻近格会共同承载能量。</p>
</section>

<section class="teaching-demo" id="timing-demo" aria-labelledby="timing-demo-title">
<h3 id="timing-demo-title">2. 同一个速度格，为什么会读出两种速度？</h3>
<p><strong>看哪里：</strong>TX1 到下一次 TX1 之间，经过了三次扫频。下面固定谱峰在中心右边第 10 格，只改变换算时采用的采样间隔。</p>
<ol class="tx-sequence" aria-label="发射顺序：TX1、TX2、TX3、TX1"><li><strong>TX1</strong><span>0 µs</span></li><li>TX2<span>160 µs</span></li><li>TX3<span>320 µs</span></li><li><strong>TX1</strong><span>480 µs</span></li></ol>
<p>同一个 TX 再次发射：<strong>480 µs = 3 × 160 µs</strong>。</p>
<div class="demo-buttons"><button type="button" data-timing="1" aria-pressed="false">按当前代码：160 µs</button><button type="button" data-timing="3" aria-pressed="true">按三路轮发：480 µs</button></div>
<p class="demo-result" id="timing-result" aria-live="polite">第 +10 格 × 0.03134 m/s/格 = +0.3134 m/s。</p>
<p id="timing-explanation">三路轮发时，同一通道每 480 µs 才有一个新点。若误用 160 µs，换算出的速度会大 3 倍；谱峰的格编号没有改变。</p>
<p class="demo-equation">计算：每格速度 Δv = λ/(2 × 128 × T)。真实采集是否按这组顺序轮发，需要查 chirp 配置。</p>
</section>

<section class="teaching-demo" id="phase-demo" aria-labelledby="phase-demo-title">
<h3 id="phase-demo-title">3. 相位变化 1 弧度，对应多大位移？</h3>
<p><strong>看哪里：</strong>下面的点代表单位幅度复数的相位；水平轴是 I，竖直轴是 Q。红色实线是当前相位，虚线是起点。拖动滑块，看转角和位移怎样对应。</p>
<label for="demo-phase">相位变化：<output id="phase-value" for="demo-phase">1.0 rad</output></label>
<input id="demo-phase" type="range" min="-3" max="3" step="0.1" value="1">
<svg class="phase-circle" viewBox="0 0 260 230" width="260" height="230" role="img" aria-labelledby="phase-svg-title"><title id="phase-svg-title">单位圆上相位变化 1 弧度</title><circle cx="125" cy="115" r="75" class="phase-outline"/><path d="M25 115H225 M125 20V210" class="phase-axis"/><text x="232" y="120">I</text><text x="135" y="22">Q</text><line x1="125" y1="115" x2="200" y2="115" class="phase-start"/><line id="phase-hand" x1="125" y1="115" x2="165.52" y2="51.89" class="phase-hand"/><circle id="phase-point" cx="165.52" cy="51.89" r="5" class="phase-point"/><text x="201" y="140">起点</text></svg>
<p class="demo-result" id="phase-result" aria-live="polite">1.0 rad × 0.30646 mm/rad = 0.30646 mm。</p>
<p>目标移动一段距离，回波要多走一个来回，所以换算用 λ/(4π)，而不是 λ/(2π)。这里采用代码的相位符号约定；正负对应靠近还是远离，要通过实验确认。</p>
<p class="demo-equation">计算：ΔR = λΔφ/(4π)。这个例子假设同一散射点持续主导回波、相位连续且噪声很小。实测中乱跳的相位不能这样直接解释。</p>
</section>

## 公式用到的参数

| 代码名 | 当前值 | 用途 |
| --- | --- | --- |
| `fs` | 10 MHz | ADC 每秒采多少点 |
| `samples` | 256 | 每次扫频采多少点 |
| `slope` | 29.982 × 10¹² Hz/s | 扫频的频率上升速率 |
| `tr` | 60 µs | 完整扫频斜坡时长 |
| `idle_time` | 100 µs | 相邻扫频之间的空闲时间 |
| `tc` | 160 µs | 一次扫频连同空闲时间 |
| `tframe_set` | 80 ms | 相邻帧的开始时刻间隔 |
| `lambda_m` | 约 3.851 mm | 速度、相位位移的换算尺度 |

## 代码怎样计算这些量

以下摘自 `project/src/iwr1443_adc_utils.py` 的 `RadarConfig.__post_init__`。

<!-- source:utils:derived:start -->
```python
self.tc = self.tr + self.idle_time
self.bandwidth = self.slope * self.tr
self.bandwidth_valid = self.samples / self.fs * self.slope
self.center_freq = self.start_freq + self.bandwidth / 2.0
self.lambda_m = self.c / self.center_freq
self.range_resolution_m = self.c / (2.0 * self.bandwidth_valid)
self.speed_resolution_mps = self.lambda_m / (2.0 * self.doppler_bin * self.tc)
```
<!-- source:utils:derived:end -->

MATLAB 中对应的计算如下（教学写法）：

```matlab
tc = tr + idle_time;
bandwidth = slope*tr;
bandwidthValid = samples/fs*slope;
centerFreq = startFreq + bandwidth/2;
wavelength = c/centerFreq;
rangeResolution = c/(2*bandwidthValid);
speedResolution = wavelength/(2*chirps*tc);
```

`bandwidth` 覆盖完整斜坡；`bandwidth_valid` 只覆盖 ADC 实际采样的 25.6 µs。距离换算用后者，得到约 0.19543 m/格。最后一行速度公式用了 `tc`，因此仍需核对[三路发射的重复间隔](../processing/doppler.md)。
