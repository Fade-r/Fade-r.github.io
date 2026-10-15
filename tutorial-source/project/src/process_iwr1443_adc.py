from __future__ import annotations

from pathlib import Path

import numpy as np

from iwr1443_adc_utils import (
    RadarConfig,
    build_capture_time_axis,
    compute_channel_correlation,
    compute_doppler_spectrum,
    compute_phase_displacement,
    compute_range_angle_heatmap,
    compute_spectrogram,
    ensure_output_dirs,
    extract_slow_time,
    frame_to_matlab_view,
    load_raw_int16,
    parse_adc_matlab,
    run_angle_fft_strict,
    run_doppler_fft_strict,
    run_range_fft,
    save_channel_plots,
    save_metadata,
    save_npz,
    save_range_angle_plot,
    save_range_plots,
    save_raw_iq_plots,
    save_signal_diagnostics,
    save_slow_time_plots,
    summarize_range_over_frames,
    validate_layout_candidates,
)


# Config section
CFG = RadarConfig(
    bin_path=Path(__file__).resolve().parents[1] / "data" / "raw" / "adc_data.bin",
    output_dir=Path(__file__).resolve().parents[1] / "outputs",
    samples=256,
    chirps=128,
    tx=3,
    rx=4,
    frame_count_override=None,
    processing_mode="strict_matlab",
    range_window="hamming",
    doppler_window="hamming",
    angle_bin=180,
    angle_channels=list(range(8)),
    frame_idx=0,
    chirp_idx=0,
    virtual_channel_idx=0,
    range_bin_idx=30,
    raw_segment_start=0,
    raw_segment_length=256,
    signal_sample_start=0,
    signal_sample_stop=128,
    tdm_validation_enabled=True,
    save_intermediates=True,
    save_full_adc_cube=False,
)


def _print_summary(parsing_summary: dict[str, object], frame0: np.ndarray, frame1: np.ndarray) -> None:
    print("=== Binary Parsing and Verification ===")
    print(f"Raw int16 length: {parsing_summary['raw_int16_length']}")
    print(f"Expected int16 per frame: {parsing_summary['per_frame_int16']}")
    print(f"Expected complex samples per frame: {parsing_summary['per_frame_complex']}")
    print(f"Detected frames: {parsing_summary['detected_frames']}")
    print(f"Selected frames: {parsing_summary['selected_frames']}")
    if parsing_summary.get("warning"):
        print(f"Warning: {parsing_summary['warning']}")
    print(f"Parsed complex sample count: {parsing_summary['parsed_complex_count']}")
    print(f"Final tensor shape: {parsing_summary['final_tensor_shape']}")
    print(f"Axis order: {parsing_summary['axis_order']}")
    print(
        "Frame 1 checkpoint (MATLAB 1-based frame=1) first samples: "
        f"{frame0[0, 0, 0].real:.0f}+{frame0[0, 0, 0].imag:.0f}j, "
        f"{frame0[1, 0, 0].real:.0f}+{frame0[1, 0, 0].imag:.0f}j"
    )
    print(
        "Frame 2 checkpoint (MATLAB 1-based frame=2) first sample: "
        f"{frame1[0, 0, 0].real:.0f}+{frame1[0, 0, 0].imag:.0f}j"
    )


def _print_assumptions(cfg: RadarConfig) -> None:
    print("\n=== Final Data Layout ===")
    print("Canonical storage: adc_cube[frame, virtual_channel, chirp, adc_sample]")
    print("MATLAB comparison view: frame_cube_matlab[adc_sample, chirp, virtual_channel]")
    print("Virtual channel order: TX1RX1..TX1RX4, TX2RX1..TX2RX4, TX3RX1..TX3RX4")

    print("\n=== Assumptions ===")
    print("- MATLAB parser is the source of truth for parsing and reshape order.")
    print("- Auto-detected frame count is used unless frame_count_override is set.")
    print("- Strict angle processing defaults to the first 8 virtual channels, matching demo.m.")
    print("- Displacement is derived from unwrapped phase using lambda / (4*pi).")

    print("\n=== MATLAB Comparison Points ===")
    print("- Compare Python frame 1 and frame 2 first complex samples against MATLAB checkpoints.")
    print("- Compare the selected-frame MATLAB-view tensor shape: (256, 128, 12).")
    print("- Compare range_profile[:, chirp_idx, virtual_channel_idx] against MATLAB range FFT.")
    print("- Confirm strict speed_profile[:, :, 4] is zero, matching the MATLAB quirk.")
    print("- Compare the strict range-angle heatmap with the MATLAB output.")

    print("\n=== Suggested Next Step ===")
    print(
        "- For bin-wise IQ micro-motion work, start from stable range-bin selection plus clutter "
        "suppression, then build a range_bin x slow_time x channel tensor for phase-field analysis."
    )
    print(
        "- After that, study channel coherence and low-rank structure with PCA or SVD across "
        "range bins and virtual channels."
    )


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

    _print_summary(parsing_summary, frame0, frame1)
    print("\n=== Layout Validation ===")
    for name, metrics in validation_report["candidates"].items():
        print(
            f"{name}: combined_score={metrics['combined_score']:.6g}, "
            f"mean_abs_chirp_diff={metrics['mean_abs_chirp_diff']:.6g}, "
            f"range_peakiness={metrics['range_peakiness']:.6g}"
        )
    print(f"Default parser winner: {validation_report['default_winner']}")
    print("\n=== Strict MATLAB FFT Checkpoints ===")
    print(f"Selected frame MATLAB-view shape: {selected_frame.shape}")
    print(f"Range profile shape: {range_profile.shape}")
    print(f"Speed profile shape: {speed_profile.shape}")
    print(f"Angle profile shape: {angle_profile.shape}")
    print(
        "Strict speed_profile channel 5 energy (Python zero-based VC 4): "
        f"{np.sum(np.abs(speed_profile[:, :, 4])):.6g}"
    )
    _print_assumptions(cfg)

    save_raw_iq_plots(raw, cfg, output_dirs["figures"])
    save_signal_diagnostics(selected_frame, cfg, output_dirs["figures"])
    save_range_plots(range_profile, average_range_profile, range_time_map, cfg, output_dirs["figures"])
    save_slow_time_plots(
        slow_time_trace,
        time_axis,
        phase,
        displacement,
        doppler,
        spectrogram,
        cfg,
        output_dirs["figures"],
    )
    save_channel_plots(channel_traces, time_axis, channel_correlation, cfg, output_dirs["figures"])
    save_range_angle_plot(angle_heatmap, cfg, output_dirs["figures"])

    metadata = {
        "config": cfg.to_metadata(),
        "parsing_summary": parsing_summary,
        "validation_report": validation_report,
        "selected_frame_shape": tuple(int(v) for v in selected_frame.shape),
        "range_profile_shape": tuple(int(v) for v in range_profile.shape),
        "speed_profile_shape": tuple(int(v) for v in speed_profile.shape),
        "angle_profile_shape": tuple(int(v) for v in angle_profile.shape),
        "channel_trace_shape": tuple(int(v) for v in channel_traces.shape),
        "slow_time_trace_length": int(slow_time_trace.size),
    }
    save_metadata(output_dirs["debug"] / "run_metadata.json", metadata)

    if cfg.save_intermediates:
        save_npz(
            output_dirs["debug"] / "selected_frame_debug.npz",
            selected_frame=selected_frame,
            range_profile=range_profile,
            speed_profile=speed_profile,
            angle_profile=angle_profile,
            angle_heatmap=angle_heatmap,
            average_range_profile=average_range_profile,
            range_time_map=range_time_map,
            channel_traces=channel_traces,
            slow_time_trace=slow_time_trace,
            slow_time_phase=phase,
            slow_time_displacement_m=displacement,
            capture_time_s=time_axis,
            doppler_freq_hz=doppler["freq_hz"],
            doppler_spectrum=doppler["spectrum"],
            spectrogram_freq_hz=spectrogram["freq_hz"],
            spectrogram_time_s=spectrogram["time_s"],
            spectrogram_matrix=spectrogram["stft"],
        )
        if cfg.save_full_adc_cube:
            save_npz(output_dirs["debug"] / "adc_cube_full.npz", adc_cube=adc_cube)

    print("\n=== Outputs Saved ===")
    print(f"Figures: {output_dirs['figures']}")
    print(f"Debug artifacts: {output_dirs['debug']}")


if __name__ == "__main__":
    main(CFG)
