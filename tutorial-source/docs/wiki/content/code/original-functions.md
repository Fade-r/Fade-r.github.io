# 原函数逐段说明

这里保留原处理程序的函数原文与行号。基础章节中的教学实现与这些函数分开，避免将历史算法问题带入新示例。各函数在整体程序中的位置见[项目代码分析](code-map.md)。

## _matlab_interleave_iq

源码位置：`project/src/iwr1443_adc_utils.py`，第 141 行。

```python linenums="141"
def _matlab_interleave_iq(raw_int16: np.ndarray) -> np.ndarray:
    if raw_int16.size % 4 != 0:
        raise ValueError(
            "MATLAB I/Q conversion expects raw int16 length to be divisible by 4; "
            f"got {raw_int16.size}."
        )

    raw_float = raw_int16.astype(np.float32, copy=False)
    complex_stream = np.empty(raw_int16.size // 2, dtype=np.complex64)
    complex_stream[0::2] = raw_float[0::4] + 1j * raw_float[2::4]
    complex_stream[1::2] = raw_float[1::4] + 1j * raw_float[3::4]
    return complex_stream
```

函数先把整数转为浮点数，再用步长为 4 的切片取出 I、Q。输入每组 `[I0,I1,Q0,Q1]`，输出 `[I0+jQ0,I1+jQ1]`，分别写到复数序列的偶数和奇数位置。xWR14xx 四路 RX 的示例格式却是 `[I0,I1,I2,I3,Q0,Q1,Q2,Q3]`；若把这种八元组送入本函数，就会把部分 I 值误当成 Q。格式对应关系见 [ADC 数据读取](../data/adc-iq-layout.md)。

## _parse_frame_matlab_view

源码位置：`project/src/iwr1443_adc_utils.py`，第 155 行。

```python linenums="155"
def _parse_frame_matlab_view(frame_raw_int16: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    complex_stream = _matlab_interleave_iq(frame_raw_int16)
    lvds_data = complex_stream.reshape((cfg.samples * cfg.virtual_channels, cfg.chirps), order="F").T
    # MATLAB loops over chirps and copies contiguous sample blocks for each virtual channel.
    cdata = lvds_data.reshape((cfg.chirps, cfg.virtual_channels, cfg.samples))
    return cdata.transpose(2, 0, 1)
```

第一次 reshape 使用 MATLAB 列优先顺序，转置后再拆为轮次、通道和采样点。最后将采样点放到第一维。所有操作都在重排同一组数值，没有增加信息。

## _parse_frame_tdm_candidate

源码位置：`project/src/iwr1443_adc_utils.py`，第 163 行。

```python linenums="163"
def _parse_frame_tdm_candidate(frame_raw_int16: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    complex_stream = _matlab_interleave_iq(frame_raw_int16)
    phys = complex_stream.reshape((cfg.chirps * cfg.tx, cfg.samples, cfg.rx))
    frame_cube = np.empty((cfg.samples, cfg.chirps, cfg.virtual_channels), dtype=np.complex64)
    # Alternate sanity-check layout: interpret the stream as physical chirps with TX cycling fastest,
    # but assume samples advance before RX within each physical chirp.
    for chirp_idx in range(cfg.chirps):
        tx_group = phys[chirp_idx * cfg.tx : (chirp_idx + 1) * cfg.tx]
        frame_cube[:, chirp_idx, :] = tx_group.transpose(1, 0, 2).reshape(cfg.samples, cfg.virtual_channels)
    return frame_cube
```

先将数据分为实际 chirp、采样点和 RX，再每三个 chirp 组成一轮，将 TX 与 RX 合为虚拟通道。它与前一个函数共用四元组 I/Q 配对，因此二者比较并未覆盖八元组格式。

## run_range_fft

!!! formula-recap "代码对应的距离 FFT"

    \[
    X_r[k,m,p]=\sum_{n=0}^{N_s-1}x[n,m,p]w[n]e^{-j2\pi kn/N_{\mathrm{FFT}}}.
    \]

    $n$ 为采样点、$m$ 为轮次、$p$ 为通道；`cfg.range_bin` 对应 $N_{\mathrm{FFT}}$。下面的乘窗和 `axis=0` 分别实现公式中的 $w[n]$ 和沿 $n$ 求和。推导见[距离测量](../processing/range.md)。

源码位置：`project/src/iwr1443_adc_utils.py`，第 247 行。

```python linenums="247"
def run_range_fft(frame_cube_matlab: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    if frame_cube_matlab.shape != (cfg.samples, cfg.chirps, cfg.virtual_channels):
        raise ValueError(
            "run_range_fft expects MATLAB-view shape "
            f"({cfg.samples}, {cfg.chirps}, {cfg.virtual_channels}), got {frame_cube_matlab.shape}."
        )
    range_window = make_window(cfg.range_window, cfg.samples).reshape(-1, 1, 1)
    windowed = frame_cube_matlab * range_window
    # Range FFT is applied along the ADC-sample dimension to match the MATLAB implementation.
    return np.fft.fft(windowed, n=cfg.range_bin, axis=0)
```

尺寸检查限定输入为采样点、轮次和通道。窗函数变为 [Ns,1,1] 后乘到所有序列，axis=0 对每个通道的单次 chirp 做 FFT。输出仍保留复数。

## run_doppler_fft_strict

源码位置：`project/src/iwr1443_adc_utils.py`，第 259 行。

```python linenums="259"
def run_doppler_fft_strict(range_profile: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    speed_profile = np.zeros_like(range_profile, dtype=np.complex128)
    doppler_window = make_window(cfg.doppler_window, cfg.chirps).reshape(1, -1, 1)
    temp = range_profile[:, :, : cfg.rx] * doppler_window
    # Strict MATLAB parity: Doppler FFT is only computed for channels 1:4.
    speed_profile[:, :, : cfg.rx] = np.fft.fftshift(
        np.fft.fft(temp, n=cfg.doppler_bin, axis=1),
        axes=1,
    )
    return speed_profile
```

输出先全部置零，只对 `:cfg.rx` 范围计算多普勒。`cfg.rx=4`，所以 12 个通道中后 8 个始终为零。测角需要比较选定阵元的相位，把未计算通道留为零就丢掉了这些观测。教学版在[速度测量](../processing/doppler.md)中对全部通道沿轮次计算，之后再按实际阵列选择测角通道。

## run_angle_fft_strict

源码位置：`project/src/iwr1443_adc_utils.py`，第 271 行。

```python linenums="271"
def run_angle_fft_strict(speed_profile: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    selected = speed_profile[:, :, cfg.angle_channels]
    # Strict MATLAB parity: angle FFT consumes the configured channel slice directly.
    return np.fft.fftshift(np.fft.fft(selected, n=cfg.angle_bin, axis=2), axes=2)
```

当前 `cfg.angle_channels` 选择前 8 个通道，函数把它们补零到 180 点。由于多普勒结果中仅前 4 通道有效，实际输入是 4 个有效值加 4 个零。对间距为 $d$ 的均匀线阵，第 $q$ 个有符号空间格应按 $\theta=\arcsin(\lambda q/(180d))$ 换算；直接把格编号标为角度会省略这个非线性关系。应用公式前还须确认选定通道确实构成该均匀线阵，详见[角度测量](../processing/angle.md)。

## compute_phase_displacement

!!! formula-recap "从复数相角恢复相对位移"

    [微位移测量](../processing/phase.md)使用
    $\Delta R=\lambda\Delta\phi/(4\pi)$。
    对输入 `trace` 的第 $i$ 个复数，先取相角并解缠，再令 $\Delta\phi_i=\phi_i-\phi_0$；因此输出以第一点为位移零点。

源码位置：`project/src/iwr1443_adc_utils.py`，第 338 行。

```python linenums="338"
def compute_phase_displacement(trace: np.ndarray, cfg: RadarConfig) -> tuple[np.ndarray, np.ndarray]:
    phase = np.unwrap(np.angle(trace))
    displacement = (phase - phase[0]) * cfg.lambda_m / (4.0 * np.pi)
    return phase, displacement
```

angle 取相位，unwrap 解缠，减去首点得到相位变化，再乘 λ/(4π) 换算为位移。这些运算没有检查目标强度，也没有验证相位是否来自同一散射点。

## _resample_complex_to_uniform

源码位置：`project/src/iwr1443_adc_utils.py`，第 320 行。

```python linenums="320"
def _resample_complex_to_uniform(trace: np.ndarray, time_axis: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    uniform_time = np.arange(time_axis[0], time_axis[-1] + dt * 0.5, dt, dtype=np.float64)
    real_uniform = np.interp(uniform_time, time_axis, trace.real)
    imag_uniform = np.interp(uniform_time, time_axis, trace.imag)
    return real_uniform + 1j * imag_uniform, uniform_time
```

`np.arange` 按间隔 `dt` 建立均匀时间轴，两个 `np.interp` 分别对实部和虚部做线性插值，最后合成为复数。相邻观测为 $z_i,z_{i+1}$ 时，补点为 $z(t)=(1-\alpha)z_i+\alpha z_{i+1}$，其中 $\alpha=(t-t_i)/(t_{i+1}-t_i)$。这在复平面中连接两点的直线，不是沿真实相位轨迹补测。返回值虽满足 FFT 的等间隔输入形式，其频谱仍受这个连线假设影响。

原记录的帧之间存在空隙。这个函数也会在空隙内连线补点，使 12,800 个实测点扩展为 49,628 个点，其中约 74% 是插值结果。插值没有增加测量信息；空隙较大时，补出的变化可能主导后续频谱。
