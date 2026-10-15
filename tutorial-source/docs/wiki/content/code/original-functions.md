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

函数先把整数转为浮点数，再用步长为 4 的切片取出 I、Q。偶数和奇数复数位置分别填入两组配对结果。这是两 I、两 Q 的四元组格式，不是 xWR14xx 四 I、四 Q 的八元组格式。

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

输出先全部置零，只对 :cfg.rx 范围计算多普勒。cfg.rx=4，所以 12 个通道中后 8 个始终为零。它复现了上游 MATLAB 的通道循环范围，不是测角前推荐的处理方式。

## run_angle_fft_strict

源码位置：`project/src/iwr1443_adc_utils.py`，第 271 行。

```python linenums="271"
def run_angle_fft_strict(speed_profile: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    selected = speed_profile[:, :, cfg.angle_channels]
    # Strict MATLAB parity: angle FFT consumes the configured channel slice directly.
    return np.fft.fftshift(np.fft.fft(selected, n=cfg.angle_bin, axis=2), axes=2)
```

函数只取前 8 个通道并补零到 180 点。由于多普勒结果中仅前 4 通道有效，实际输入是 4 个有效值加 4 个零。180 个格是空间频率采样点，不能直接标成角度。

## compute_phase_displacement

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

`np.arange` 按间隔 `dt` 建立均匀时间轴，两个 `np.interp` 分别对实部和虚部做线性插值，最后合成为复数。返回的序列可以直接送入要求等间隔采样的 FFT。

原记录的帧之间存在空隙。这个函数也会在空隙内连线补点，使 12,800 个实测点扩展为 49,628 个点，其中约 74% 是插值结果。插值没有增加测量信息；空隙较大时，补出的变化可能主导后续频谱。
