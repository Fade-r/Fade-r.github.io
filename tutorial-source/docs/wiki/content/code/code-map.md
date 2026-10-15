# 把教程步骤对应到项目代码

学完前面的简化实现，再看项目就容易分清：哪些函数负责算数，哪些只是组织流程和保存图片。这里讲的是当前真实代码；教程示例保存在 `docs/wiki/examples/`，没有替换生产处理程序。

## 1. 五个源文件分别负责什么

| 文件 | 你应该怎样读它 |
| --- | --- |
| `project/src/process_iwr1443_adc.py` | 先看 `CFG` 配置，再看 `main`。它决定先后调用哪些函数、选哪一帧和哪一个距离格。 |
| `project/src/iwr1443_adc_utils.py` | 实际计算都在这里：读取、重排、FFT、跨帧汇总、相位和绘图。按调用关系读，不必从第一行背到最后。 |
| `references/pku-mmwave-tutorial/generateParameter.m` | MATLAB 参数表。注意采样点数、轮次、发射数、接收数和时间单位。 |
| `references/pku-mmwave-tutorial/DCA1000_Read_Data.m` | 用全局变量选择一帧，配 I/Q，按通道复制数据，再组成三维数组。 |
| `references/pku-mmwave-tutorial/demo.m` | 原教程的执行入口：三次 FFT 后绘图。Python 的 `strict` 行为主要参照它。 |

## 2. Python 的 main 真正怎样走

以下是 `process_iwr1443_adc.py` 第 117–145 行原文：

```python linenums="117"
def main(cfg: RadarConfig) -> None:
    output_dirs = ensure_output_dirs(cfg)
    raw = load_raw_int16(cfg.bin_path)
    validation_report = validate_layout_candidates(raw, cfg)
    adc_cube, parsing_summary = parse_adc_matlab(raw, cfg)

    if cfg.frame_idx >= adc_cube.shape[0]:
        raise IndexError(
            f"frame_idx={cfg.frame_idx} is out of range for parsed cube with {adc_cube.shape[0]} frames."
        )

    frame0 = frame_to_matlab_view(adc_cube, 0)
    frame1 = frame_to_matlab_view(adc_cube, 1 if adc_cube.shape[0] > 1 else 0)
    selected_frame = frame_to_matlab_view(adc_cube, cfg.frame_idx)
    range_profile = run_range_fft(selected_frame, cfg)
    speed_profile = run_doppler_fft_strict(range_profile, cfg)
    angle_profile = run_angle_fft_strict(speed_profile, cfg)
    angle_heatmap = compute_range_angle_heatmap(angle_profile)

    summaries = summarize_range_over_frames(adc_cube, cfg)
    average_range_profile = summaries["average_range_profile"]
    range_time_map = summaries["range_time_map"]
    channel_traces = summaries["channel_traces"]
    slow_time_trace = extract_slow_time(channel_traces, cfg)
    time_axis = build_capture_time_axis(cfg, adc_cube.shape[0])
    phase, displacement = compute_phase_displacement(slow_time_trace, cfg)
    doppler = compute_doppler_spectrum(slow_time_trace, cfg, time_axis)
    spectrogram = compute_spectrogram(slow_time_trace, cfg, time_axis)
    channel_correlation = compute_channel_correlation(channel_traces)
```

按三段读它：

1. `load_raw_int16` 读整数，`validate_layout_candidates` 生成比较报告，`parse_adc_matlab` 实际解析。报告和解析是先后调用，但报告没有决定采用哪种排列。
2. 从所有数据里取出 `selected_frame`，依次算距离、Doppler、角度，供单帧诊断图使用。
3. `summarize_range_over_frames` 重新遍历**全部帧**，逐帧计算距离 FFT，汇总距离图和选定距离格的复数序列。它不是从前面的单帧角度结果继续往下算。

```text
adc_cube：全部帧
  ├─ selected_frame：选定一帧
  │    └─ 距离 FFT → Doppler FFT → 角度 FFT → 单帧角图
  └─ summarize_range_over_frames：逐帧做距离 FFT
       ├─ 各帧幅度 → 平均距离谱、距离—时间图
       └─ 固定距离格的复数值 → 相位、频谱、通道比较
```

这里最值得养成的读代码习惯是：跟着变量从哪里来、传到哪里去，而不是只按函数名想象流程。

## 3. 工具模块逐段导航

下面行号以当前 `iwr1443_adc_utils.py` 为准。

| 函数与位置 | 输入、输出和作用 |
| --- | --- |
| `RadarConfig`，29 行 | 保存配置；`__post_init__` 推导带宽、波长和格间距。`processing_mode` 虽被保存，目前没有真正控制解析分支。 |
| `_to_serializable`，12 行 | 把 Path、NumPy 标量、数组等转换成 JSON 能保存的对象。不是信号处理。 |
| `expected_int16_per_frame` / `expected_complex_per_frame`，82 / 86 行 | 用采样点、轮次和通道数计算每帧长度；整数数目比复数数目多一倍。 |
| `ensure_output_dirs`，90 行 | 创建 `figures`、`debug` 目录，返回路径。 |
| `load_raw_int16`，98 行 | 文件路径 → 一维整数数组，并拒绝空文件。 |
| `resolve_frame_count`，105 行 | 检查整除、计算帧数、处理用户指定的帧数上限。 |
| `_matlab_interleave_iq`，141 行 | 四个整数 → 两个复数。 |
| `_parse_frame_matlab_view`，155 行 | 按教程连续块假设得到 `[采样点,轮次,通道]`。 |
| `_parse_frame_tdm_candidate`，163 行 | 按另一种 RX/TX 排列假设得到相同形状，用于比较。 |
| `frame_to_matlab_view`，175 行 | 从多帧数组取一帧，调换轴顺序。 |
| `parse_adc_matlab`，181 行 | 循环解析各帧，保存为 `[帧,通道,轮次,采样点]`，并返回解析摘要。 |
| `_candidate_metrics`，201 行 | 对首通道计算轮次方向相邻差、距离谱峰值与均值之比；综合分数为后者除以前者。 |
| `validate_layout_candidates`，217 行 | 仅比较首帧，生成报告；`default_winner` 固定写成教程排列。 |
| `make_window`，236 行 | 根据名字产生矩形、Hamming 或 Hann 窗。 |
| `run_range_fft`，247 行 | 沿采样点加窗和 FFT。[距离章](../processing/range.md)逐行解释。 |
| `run_doppler_fft_strict`，259 行 | 只对前 4 通道沿轮次 FFT 并移位。[速度章](../processing/doppler.md)解释遗漏。 |
| `run_angle_fft_strict`，271 行 | 选前 8 通道，沿通道补零到 180 点。[角度章](../processing/angle.md)解释适用条件。 |
| `compute_range_angle_heatmap`，277 行 | 在 Doppler 维上累加角度谱的幅度，不是累加复数或功率。 |
| `summarize_range_over_frames`，281 行 | 每帧做距离 FFT，形成平均距离谱、距离—时间图、固定距离格的各通道复数序列。 |
| `build_capture_time_axis`，309 行 | 帧起点加轮次偏移；目前偏移使用 `Tc`。 |
| `_resample_complex_to_uniform`，320 行 | 对实部和虚部线性插值，跨过帧间空隙。 |
| `extract_slow_time`，327 行 | 从汇总矩阵选出一个通道；传入完整四维数组时会先调用汇总。 |
| `compute_phase_displacement`，338 行 | 取相位、解缠、减起点，再乘 λ/(4π)。 |
| `compute_doppler_spectrum`，344 行 | 对跨帧插值序列加窗并 FFT，和单帧 Doppler 不是同一条计算。 |
| `compute_spectrogram`，360 行 | 对同样的插值序列做 STFT，即滑动窗口内的频谱。 |
| `compute_channel_correlation`，383 行 | 计算通道序列归一化复内积的模，没有去均值，不是 Pearson 相关。 |
| `save_npz` / `save_metadata`，389 / 393 行 | 保存数值和配置，便于复查。 |
| `_import_matplotlib`，397 行 | 初始化非交互绘图环境。 |
| `save_raw_iq_plots` / `save_signal_diagnostics`，410 / 432 行 | 画原始整数、单次扫频 I/Q、幅度、相位和散点。 |
| `save_range_plots` / `save_slow_time_plots`，470 / 518 行 | 画距离结果和跨帧的相位、频谱、STFT。 |
| `save_channel_plots` / `save_range_angle_plot`，586 / 636 行 | 画通道比较和角度索引热图。 |

## 4. MATLAB 三个文件要特别看哪些行

### generateParameter.m：参数与派生量

`Samples=256`、`Chirps=128`、`txNum=3`、`rxNum=4` 对应每帧数据量。`Bandwidth` 用完整斜坡时长，`BandwidthValid` 用实际 ADC 采样时长。原注释对“有效带宽”的描述容易混淆，应以表达式为准。`numCPI=50` 只是这里的设置，不能当作本次文件实际帧数。

### DCA1000_Read_Data.m：从全局帧号读出一帧

它先读取文件前 `frame` 帧，再切出最后一帧。因此 frame 越大，会重复读更多前面的数据。配 I/Q 后，`reshape`、非共轭转置 `.'` 和两层循环把连续块复制到各通道；最后逐个赋给 `data_radar(:,:,1)` 到 `(:,:,12)`。

原始 I/Q 循环的上界是 `fileSize-5`，末尾两个复数保持零。Python 已覆盖所有完整四元组，所以两者并非每个样本都完全相同。新写实现时可以用[数据章](../data/adc-iq-layout.md)的向量化版本。

### demo.m：三次 FFT 与绘图

距离部分的通道循环到 `txNum*rxNum`，多普勒部分却只到 `rxNum`；角度再取 `temp(1:8)`，其中后 4 个已经为零。`Azimuth_Index=-90:89` 是格编号，被图标成了度；`Range_Index` 从 1 而非 0 开始，有一格偏移。三处分别对应[速度](../processing/doppler.md)、[方向](../processing/angle.md)、[距离](../processing/range.md)章节的解释。

本地 `demo.m` 是上游派生文件，有两条 lint 注释和盘符修改；另外两个 MATLAB 文件与核验的上游提交逐字节一致。具体来源见[参考页](../reference/sources.md)。

## 5. 怎样用中间结果定位错误

不要先盯最后的热图。用 `project/outputs/debug/selected_frame_debug.npz` 逐层检查：

```python
import numpy as np
with np.load('project/outputs/debug/selected_frame_debug.npz') as data:
    print(data['selected_frame'].shape)  # (256,128,12)
    print(data['speed_profile'].shape)   # (256,128,12)
    print(np.max(np.abs(data['speed_profile'][:,:,4:])))  # 当前应为 0
```

MATLAB 不能把 NPZ 当作 MAT 文件直接 `load`。对照两种实现时，可以在 Python 中用 `scipy.io.savemat` 另存一份选定的小数组，再在 MATLAB 用 `load`；同时写下维度顺序、dtype 和来源，不必导出整份原始数据。

```python
from scipy.io import savemat
# selected_frame 是已取得的单帧数组；文件另存，不覆盖原始数据
savemat('workbench/experiments/wiki-build/frame_for_matlab.mat', {'frame': selected_frame})
```

```matlab
S = load('workbench/experiments/wiki-build/frame_for_matlab.mat');
frame = S.frame;
```

先比较解析后的复数，再比较距离 FFT，再比较速度和角度。上游一步不一致，后面的差异暂时没有解释价值。
