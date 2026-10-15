from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal


def _to_serializable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, list):
        return [_to_serializable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_serializable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_serializable(val) for key, val in value.items()}
    return value


@dataclass
class RadarConfig:
    bin_path: Path = Path(__file__).resolve().parents[1] / "data" / "raw" / "adc_data.bin"
    output_dir: Path = Path(__file__).resolve().parents[1] / "outputs"
    samples: int = 256
    chirps: int = 128
    tx: int = 3
    rx: int = 4
    frame_count_override: int | None = None
    processing_mode: str = "strict_matlab"
    range_window: str = "hamming"
    doppler_window: str = "hamming"
    angle_bin: int = 180
    angle_channels: list[int] = field(default_factory=lambda: list(range(8)))
    frame_idx: int = 0
    chirp_idx: int = 0
    virtual_channel_idx: int = 0
    range_bin_idx: int = 30
    raw_segment_start: int = 0
    raw_segment_length: int = 256
    signal_sample_start: int = 0
    signal_sample_stop: int = 128
    tdm_validation_enabled: bool = True
    save_intermediates: bool = True
    save_full_adc_cube: bool = False
    c: float = 3.0e8
    start_freq: float = 77.0e9
    tr: float = 60.0e-6
    idle_time: float = 100.0e-6
    fs: float = 10.0e6
    tframe_set: float = 80.0e-3
    slope: float = 29.982e12

    def __post_init__(self) -> None:
        self.bin_path = Path(self.bin_path)
        self.output_dir = Path(self.output_dir)
        self.angle_channels = list(self.angle_channels)
        self.range_bin = self.samples
        self.doppler_bin = self.chirps
        self.virtual_channels = self.tx * self.rx
        self.tc = self.tr + self.idle_time
        self.bandwidth = self.slope * self.tr
        self.bandwidth_valid = self.samples / self.fs * self.slope
        self.center_freq = self.start_freq + self.bandwidth / 2.0
        self.lambda_m = self.c / self.center_freq
        self.range_resolution_m = self.c / (2.0 * self.bandwidth_valid)
        self.speed_resolution_mps = self.lambda_m / (2.0 * self.doppler_bin * self.tc)
        self.raw_segment_length = max(8, int(self.raw_segment_length))
        self.signal_sample_stop = max(self.signal_sample_start + 8, int(self.signal_sample_stop))

    def to_metadata(self) -> dict[str, Any]:
        return _to_serializable(asdict(self))


def expected_int16_per_frame(cfg: RadarConfig) -> int:
    return cfg.samples * cfg.chirps * cfg.virtual_channels * 2


def expected_complex_per_frame(cfg: RadarConfig) -> int:
    return cfg.samples * cfg.chirps * cfg.virtual_channels


def ensure_output_dirs(cfg: RadarConfig) -> dict[str, Path]:
    figures_dir = cfg.output_dir / "figures"
    debug_dir = cfg.output_dir / "debug"
    figures_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)
    return {"root": cfg.output_dir, "figures": figures_dir, "debug": debug_dir}


def load_raw_int16(path: Path) -> np.ndarray:
    raw = np.fromfile(path, dtype=np.int16)
    if raw.size == 0:
        raise ValueError(f"No int16 samples were read from {path}.")
    return raw


def resolve_frame_count(raw: np.ndarray, cfg: RadarConfig) -> tuple[int, dict[str, Any]]:
    per_frame_int16 = expected_int16_per_frame(cfg)
    raw_length = int(raw.size)
    if raw_length % per_frame_int16 != 0:
        raise ValueError(
            "Raw int16 length does not divide evenly into MATLAB-sized frames: "
            f"raw_length={raw_length}, per_frame_int16={per_frame_int16}."
        )

    detected_frames = raw_length // per_frame_int16
    selected_frames = detected_frames
    warning = None
    if cfg.frame_count_override is not None:
        if cfg.frame_count_override > detected_frames:
            raise ValueError(
                "Configured frame_count_override exceeds detected frame count: "
                f"override={cfg.frame_count_override}, detected={detected_frames}."
            )
        selected_frames = cfg.frame_count_override
        if cfg.frame_count_override != detected_frames:
            warning = (
                "Configured frame_count_override differs from auto-detected frame count; "
                f"using first {selected_frames} frames out of detected {detected_frames}."
            )

    summary = {
        "raw_int16_length": raw_length,
        "per_frame_int16": per_frame_int16,
        "per_frame_complex": expected_complex_per_frame(cfg),
        "detected_frames": detected_frames,
        "selected_frames": selected_frames,
        "warning": warning,
    }
    return selected_frames, summary


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


def _parse_frame_matlab_view(frame_raw_int16: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    complex_stream = _matlab_interleave_iq(frame_raw_int16)
    lvds_data = complex_stream.reshape((cfg.samples * cfg.virtual_channels, cfg.chirps), order="F").T
    # MATLAB loops over chirps and copies contiguous sample blocks for each virtual channel.
    cdata = lvds_data.reshape((cfg.chirps, cfg.virtual_channels, cfg.samples))
    return cdata.transpose(2, 0, 1)


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


def frame_to_matlab_view(adc_cube: np.ndarray, frame_idx: int) -> np.ndarray:
    if not 0 <= frame_idx < adc_cube.shape[0]:
        raise IndexError(f"frame_idx={frame_idx} is out of range for {adc_cube.shape[0]} frames.")
    return adc_cube[frame_idx].transpose(2, 1, 0)


def parse_adc_matlab(raw: np.ndarray, cfg: RadarConfig) -> tuple[np.ndarray, dict[str, Any]]:
    selected_frames, summary = resolve_frame_count(raw, cfg)
    per_frame_int16 = expected_int16_per_frame(cfg)
    adc_cube = np.empty(
        (selected_frames, cfg.virtual_channels, cfg.chirps, cfg.samples),
        dtype=np.complex64,
    )

    for frame_idx in range(selected_frames):
        start = frame_idx * per_frame_int16
        stop = start + per_frame_int16
        frame_matlab = _parse_frame_matlab_view(raw[start:stop], cfg)
        adc_cube[frame_idx] = frame_matlab.transpose(2, 1, 0)

    summary["parsed_complex_count"] = int(adc_cube.size)
    summary["final_tensor_shape"] = tuple(int(v) for v in adc_cube.shape)
    summary["axis_order"] = "(frame, virtual_channel, chirp, adc_sample)"
    return adc_cube, summary


def _candidate_metrics(frame_cube_matlab: np.ndarray, cfg: RadarConfig) -> dict[str, float]:
    selected = frame_cube_matlab[:, :, 0]
    continuity = float(np.mean(np.abs(np.diff(selected, axis=1))))
    window = make_window(cfg.range_window, cfg.samples)
    range_profile = np.fft.fft(selected[:, 0] * window, n=cfg.range_bin)
    peakiness = float(np.max(np.abs(range_profile)) / (np.mean(np.abs(range_profile)) + 1e-9))
    energy = float(np.mean(np.abs(selected)))
    combined = float(peakiness / (continuity + 1e-9))
    return {
        "mean_abs_chirp_diff": continuity,
        "range_peakiness": peakiness,
        "mean_abs_signal": energy,
        "combined_score": combined,
    }


def validate_layout_candidates(raw: np.ndarray, cfg: RadarConfig) -> dict[str, Any]:
    per_frame_int16 = expected_int16_per_frame(cfg)
    if raw.size < per_frame_int16:
        raise ValueError("Need at least one MATLAB-sized frame to validate layout candidates.")

    first_frame = raw[:per_frame_int16]
    strict_frame = _parse_frame_matlab_view(first_frame, cfg)
    report: dict[str, Any] = {
        "default_winner": "strict_matlab",
        "candidates": {"strict_matlab": _candidate_metrics(strict_frame, cfg)},
    }
    if cfg.tdm_validation_enabled:
        report["candidates"]["tdm_candidate"] = _candidate_metrics(
            _parse_frame_tdm_candidate(first_frame, cfg),
            cfg,
        )
    return report


def make_window(name: str, length: int) -> np.ndarray:
    key = name.lower()
    if key in {"none", "rect", "rectangular", "boxcar"}:
        return np.ones(length, dtype=np.float32)
    if key == "hamming":
        return signal.windows.hamming(length, sym=True).astype(np.float32)
    if key in {"hann", "hanning"}:
        return signal.windows.hann(length, sym=True).astype(np.float32)
    raise ValueError(f"Unsupported window type: {name}")


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


def run_angle_fft_strict(speed_profile: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    selected = speed_profile[:, :, cfg.angle_channels]
    # Strict MATLAB parity: angle FFT consumes the configured channel slice directly.
    return np.fft.fftshift(np.fft.fft(selected, n=cfg.angle_bin, axis=2), axes=2)


def compute_range_angle_heatmap(angle_profile: np.ndarray) -> np.ndarray:
    return np.sum(np.abs(angle_profile), axis=1)


def summarize_range_over_frames(adc_cube: np.ndarray, cfg: RadarConfig) -> dict[str, np.ndarray]:
    total_frames = adc_cube.shape[0]
    range_time_map = np.zeros((total_frames, cfg.range_bin), dtype=np.float32)
    average_range_profile = np.zeros(cfg.range_bin, dtype=np.float64)
    channel_traces = np.zeros((cfg.virtual_channels, total_frames * cfg.chirps), dtype=np.complex64)
    slow_time_range_profiles = np.zeros((total_frames * cfg.chirps, cfg.range_bin), dtype=np.complex64)

    for frame_idx in range(total_frames):
        frame_matlab = frame_to_matlab_view(adc_cube, frame_idx)
        range_profile = run_range_fft(frame_matlab, cfg)
        magnitude = np.abs(range_profile[:, :, cfg.virtual_channel_idx])
        average_range_profile += np.mean(magnitude, axis=1)
        range_time_map[frame_idx] = np.mean(magnitude, axis=1).astype(np.float32)

        start = frame_idx * cfg.chirps
        stop = start + cfg.chirps
        channel_traces[:, start:stop] = range_profile[cfg.range_bin_idx, :, :].T.astype(np.complex64)
        slow_time_range_profiles[start:stop] = range_profile[:, :, cfg.virtual_channel_idx].T.astype(np.complex64)

    average_range_profile /= float(total_frames)
    return {
        "average_range_profile": average_range_profile.astype(np.float32),
        "range_time_map": range_time_map,
        "channel_traces": channel_traces,
        "slow_time_range_profiles": slow_time_range_profiles,
    }


def build_capture_time_axis(cfg: RadarConfig, total_frames: int) -> np.ndarray:
    times = np.empty(total_frames * cfg.chirps, dtype=np.float64)
    idx = 0
    for frame_idx in range(total_frames):
        frame_start = frame_idx * cfg.tframe_set
        chirp_offsets = np.arange(cfg.chirps, dtype=np.float64) * cfg.tc
        times[idx : idx + cfg.chirps] = frame_start + chirp_offsets
        idx += cfg.chirps
    return times


def _resample_complex_to_uniform(trace: np.ndarray, time_axis: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    uniform_time = np.arange(time_axis[0], time_axis[-1] + dt * 0.5, dt, dtype=np.float64)
    real_uniform = np.interp(uniform_time, time_axis, trace.real)
    imag_uniform = np.interp(uniform_time, time_axis, trace.imag)
    return real_uniform + 1j * imag_uniform, uniform_time


def extract_slow_time(adc_cube_or_range_cube: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    if adc_cube_or_range_cube.ndim == 4 and adc_cube_or_range_cube.shape[-1] == cfg.samples:
        summaries = summarize_range_over_frames(adc_cube_or_range_cube, cfg)
        return summaries["channel_traces"][cfg.virtual_channel_idx]
    if adc_cube_or_range_cube.ndim == 2:
        return adc_cube_or_range_cube[cfg.virtual_channel_idx]
    raise ValueError(
        "extract_slow_time expects either the canonical ADC cube or a channel-trace matrix."
    )


def compute_phase_displacement(trace: np.ndarray, cfg: RadarConfig) -> tuple[np.ndarray, np.ndarray]:
    phase = np.unwrap(np.angle(trace))
    displacement = (phase - phase[0]) * cfg.lambda_m / (4.0 * np.pi)
    return phase, displacement


def compute_doppler_spectrum(trace: np.ndarray, cfg: RadarConfig, time_axis: np.ndarray) -> dict[str, np.ndarray]:
    resampled_trace, uniform_time = _resample_complex_to_uniform(trace, time_axis, cfg.tc)
    if resampled_trace.size < 8:
        raise ValueError("Need at least 8 slow-time samples to compute a Doppler spectrum.")

    window = make_window("hamming", resampled_trace.size)
    spectrum = np.fft.fftshift(np.fft.fft(resampled_trace * window))
    freqs = np.fft.fftshift(np.fft.fftfreq(resampled_trace.size, d=cfg.tc))
    return {
        "uniform_time": uniform_time,
        "resampled_trace": resampled_trace,
        "freq_hz": freqs,
        "spectrum": spectrum,
    }


def compute_spectrogram(trace: np.ndarray, cfg: RadarConfig, time_axis: np.ndarray) -> dict[str, np.ndarray]:
    resampled_trace, uniform_time = _resample_complex_to_uniform(trace, time_axis, cfg.tc)
    nperseg = min(256, max(32, 2 ** int(np.floor(np.log2(max(32, resampled_trace.size // 8))))))
    noverlap = max(0, int(0.75 * nperseg))
    freqs, times, stft_matrix = signal.stft(
        resampled_trace,
        fs=1.0 / cfg.tc,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        boundary=None,
        padded=False,
        return_onesided=False,
    )
    order = np.argsort(freqs)
    return {
        "uniform_time": uniform_time,
        "freq_hz": freqs[order],
        "time_s": times + uniform_time[0],
        "stft": stft_matrix[order],
    }


def compute_channel_correlation(channel_traces: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(channel_traces, axis=1, keepdims=True)
    normalized = channel_traces / np.maximum(norms, 1e-12)
    return np.abs(normalized @ normalized.conj().T)


def save_npz(path: Path, **arrays: np.ndarray) -> None:
    np.savez_compressed(path, **arrays)


def save_metadata(path: Path, metadata: dict[str, Any]) -> None:
    path.write_text(json.dumps(_to_serializable(metadata), indent=2), encoding="utf-8")


def _import_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "matplotlib is required for figure output. Install it with `pip install matplotlib`."
        ) from exc
    return plt


def save_raw_iq_plots(raw: np.ndarray, cfg: RadarConfig, figures_dir: Path) -> None:
    plt = _import_matplotlib()
    start = int(cfg.raw_segment_start)
    stop = min(raw.size, start + cfg.raw_segment_length)
    segment = raw[start:stop]
    if segment.size < 8:
        raise ValueError("Raw segment is too short for diagnostic plotting.")

    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(segment, linewidth=1.0)
    axes[0].set_title("Raw int16 Segment")
    axes[0].set_ylabel("Amplitude")
    axes[1].plot(segment[0::2], label="Even index", linewidth=1.0)
    axes[1].plot(segment[1::2], label="Odd index", linewidth=1.0)
    axes[1].set_title("Raw int16 Even/Odd Split")
    axes[1].set_xlabel("Sample index")
    axes[1].legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(figures_dir / "raw_int16_segment.png", dpi=150)
    plt.close(fig)


def save_signal_diagnostics(frame_cube_matlab: np.ndarray, cfg: RadarConfig, figures_dir: Path) -> None:
    plt = _import_matplotlib()
    sample_slice = slice(cfg.signal_sample_start, min(cfg.signal_sample_stop, cfg.samples))
    trace = frame_cube_matlab[sample_slice, cfg.chirp_idx, cfg.virtual_channel_idx]
    sample_indices = np.arange(trace.size) + sample_slice.start

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(sample_indices, trace.real, label="I", linewidth=1.0)
    axes[0].plot(sample_indices, trace.imag, label="Q", linewidth=1.0)
    axes[0].set_ylabel("Amplitude")
    axes[0].set_title("Selected Complex Signal")
    axes[0].legend(loc="upper right")
    axes[1].plot(sample_indices, np.abs(trace), linewidth=1.0)
    axes[1].set_ylabel("Magnitude")
    axes[2].plot(sample_indices, np.angle(trace), linewidth=1.0)
    axes[2].set_ylabel("Phase (rad)")
    axes[2].set_xlabel("ADC sample index")
    fig.tight_layout()
    fig.savefig(
        figures_dir / f"signal_frame{cfg.frame_idx:03d}_chirp{cfg.chirp_idx:03d}_vc{cfg.virtual_channel_idx:02d}.png",
        dpi=150,
    )
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(trace.real, trace.imag, s=18, alpha=0.8)
    ax.set_title("IQ Constellation")
    ax.set_xlabel("I")
    ax.set_ylabel("Q")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        figures_dir / f"iq_constellation_frame{cfg.frame_idx:03d}_chirp{cfg.chirp_idx:03d}_vc{cfg.virtual_channel_idx:02d}.png",
        dpi=150,
    )
    plt.close(fig)


def save_range_plots(
    range_profile: np.ndarray,
    average_range_profile: np.ndarray,
    range_time_map: np.ndarray,
    cfg: RadarConfig,
    figures_dir: Path,
) -> None:
    plt = _import_matplotlib()
    range_axis = np.arange(cfg.range_bin) * cfg.range_resolution_m

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(range_axis, np.abs(range_profile[:, cfg.chirp_idx, cfg.virtual_channel_idx]), linewidth=1.0)
    ax.set_title("Range Profile for Selected Chirp and Channel")
    ax.set_xlabel("Range (m)")
    ax.set_ylabel("Magnitude")
    fig.tight_layout()
    fig.savefig(
        figures_dir / f"range_profile_frame{cfg.frame_idx:03d}_chirp{cfg.chirp_idx:03d}_vc{cfg.virtual_channel_idx:02d}.png",
        dpi=150,
    )
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(range_axis, average_range_profile, linewidth=1.0)
    ax.set_title("Average Range Profile Across Frames and Chirps")
    ax.set_xlabel("Range (m)")
    ax.set_ylabel("Average magnitude")
    fig.tight_layout()
    fig.savefig(figures_dir / "average_range_profile.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(
        range_time_map.T,
        aspect="auto",
        origin="lower",
        extent=(0, range_time_map.shape[0] - 1, range_axis[0], range_axis[-1]),
        cmap="viridis",
    )
    ax.set_title(f"Range-Time Map for VC {cfg.virtual_channel_idx}")
    ax.set_xlabel("Frame index")
    ax.set_ylabel("Range (m)")
    fig.colorbar(im, ax=ax, label="Magnitude")
    fig.tight_layout()
    fig.savefig(figures_dir / f"range_time_vc{cfg.virtual_channel_idx:02d}.png", dpi=150)
    plt.close(fig)


def save_slow_time_plots(
    trace: np.ndarray,
    time_axis: np.ndarray,
    phase: np.ndarray,
    displacement: np.ndarray,
    doppler: dict[str, np.ndarray],
    spectrogram: dict[str, np.ndarray],
    cfg: RadarConfig,
    figures_dir: Path,
) -> None:
    plt = _import_matplotlib()

    fig, axes = plt.subplots(4, 1, figsize=(11, 10), sharex=False)
    axes[0].plot(trace.real, trace.imag, linewidth=1.0)
    axes[0].set_title("Slow-Time IQ Trajectory")
    axes[0].set_xlabel("I")
    axes[0].set_ylabel("Q")
    axes[1].plot(time_axis, trace.real, label="I", linewidth=1.0)
    axes[1].plot(time_axis, trace.imag, label="Q", linewidth=1.0)
    axes[1].set_title("Slow-Time Waveform")
    axes[1].set_ylabel("Amplitude")
    axes[1].legend(loc="upper right")
    axes[2].plot(time_axis, phase, linewidth=1.0)
    axes[2].set_title("Unwrapped Phase")
    axes[2].set_ylabel("Phase (rad)")
    axes[3].plot(time_axis, displacement * 1e3, linewidth=1.0)
    axes[3].set_title("Displacement from Phase")
    axes[3].set_ylabel("Displacement (mm)")
    axes[3].set_xlabel("Time (s)")
    fig.tight_layout()
    fig.savefig(
        figures_dir / f"slow_time_rangebin{cfg.range_bin_idx:03d}_vc{cfg.virtual_channel_idx:02d}.png",
        dpi=150,
    )
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(doppler["freq_hz"], np.abs(doppler["spectrum"]), linewidth=1.0)
    ax.set_title("Slow-Time Doppler Spectrum")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude")
    fig.tight_layout()
    fig.savefig(
        figures_dir / f"doppler_spectrum_rangebin{cfg.range_bin_idx:03d}_vc{cfg.virtual_channel_idx:02d}.png",
        dpi=150,
    )
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.pcolormesh(
        spectrogram["time_s"],
        spectrogram["freq_hz"],
        np.abs(spectrogram["stft"]),
        shading="auto",
        cmap="magma",
    )
    ax.set_title("Slow-Time Spectrogram")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    fig.colorbar(im, ax=ax, label="Magnitude")
    fig.tight_layout()
    fig.savefig(
        figures_dir / f"spectrogram_rangebin{cfg.range_bin_idx:03d}_vc{cfg.virtual_channel_idx:02d}.png",
        dpi=150,
    )
    plt.close(fig)


def save_channel_plots(
    channel_traces: np.ndarray,
    time_axis: np.ndarray,
    correlation: np.ndarray,
    cfg: RadarConfig,
    figures_dir: Path,
) -> None:
    plt = _import_matplotlib()
    phase = np.unwrap(np.angle(channel_traces), axis=1)
    channels = channel_traces.shape[0]
    cols = 3
    rows = int(np.ceil(channels / cols))

    fig, axes = plt.subplots(rows, cols, figsize=(14, 10), squeeze=False)
    for chan_idx in range(channels):
        ax = axes[chan_idx // cols, chan_idx % cols]
        ax.plot(channel_traces[chan_idx].real, channel_traces[chan_idx].imag, linewidth=0.8)
        ax.set_title(f"VC {chan_idx}")
        ax.set_xlabel("I")
        ax.set_ylabel("Q")
    for empty_idx in range(channels, rows * cols):
        axes[empty_idx // cols, empty_idx % cols].axis("off")
    fig.tight_layout()
    fig.savefig(figures_dir / f"channel_iq_grid_rangebin{cfg.range_bin_idx:03d}.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(rows, cols, figsize=(14, 10), squeeze=False, sharex=True)
    for chan_idx in range(channels):
        ax = axes[chan_idx // cols, chan_idx % cols]
        ax.plot(time_axis, phase[chan_idx], linewidth=0.8)
        ax.set_title(f"VC {chan_idx}")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Phase (rad)")
    for empty_idx in range(channels, rows * cols):
        axes[empty_idx // cols, empty_idx % cols].axis("off")
    fig.tight_layout()
    fig.savefig(figures_dir / f"channel_phase_grid_rangebin{cfg.range_bin_idx:03d}.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(correlation, vmin=0.0, vmax=1.0, cmap="viridis")
    ax.set_title("Channel Correlation Matrix")
    ax.set_xlabel("Virtual channel")
    ax.set_ylabel("Virtual channel")
    fig.colorbar(im, ax=ax, label="Normalized correlation")
    fig.tight_layout()
    fig.savefig(figures_dir / f"channel_correlation_rangebin{cfg.range_bin_idx:03d}.png", dpi=150)
    plt.close(fig)


def save_range_angle_plot(angle_heatmap: np.ndarray, cfg: RadarConfig, figures_dir: Path) -> None:
    plt = _import_matplotlib()
    range_axis = np.arange(cfg.range_bin) * cfg.range_resolution_m
    azimuth_axis = np.arange(-cfg.angle_bin // 2, cfg.angle_bin // 2)

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(
        angle_heatmap,
        aspect="auto",
        origin="lower",
        extent=(azimuth_axis[0], azimuth_axis[-1], range_axis[0], range_axis[-1]),
        cmap="viridis",
    )
    ax.set_title("Strict MATLAB Range-Angle Heatmap")
    ax.set_xlabel("Azimuth index")
    ax.set_ylabel("Range (m)")
    fig.colorbar(im, ax=ax, label="Magnitude")
    fig.tight_layout()
    fig.savefig(figures_dir / "range_angle_heatmap_strict.png", dpi=150)
    plt.close(fig)
