"""Ideal point target and calibrated half-wave ULA, not measured IWR1443 data.
Channels are simultaneous or already TDM-compensated. No input files needed.
"""
import numpy as np


def ca_cfar(power, training=8, guard=2, pfa=1e-3):
    count = 2 * training
    alpha = count * (pfa ** (-1 / count) - 1)
    threshold = np.full(power.shape, np.nan, dtype=float)
    detected = np.zeros(power.shape, dtype=bool)
    for k in range(training + guard, len(power) - training - guard):
        left = power[k - guard - training:k - guard]
        right = power[k + guard + 1:k + guard + training + 1]
        noise = np.mean(np.concatenate((left, right)))
        threshold[k] = alpha * noise
        detected[k] = power[k] > threshold[k]
    return detected, threshold


def main():
    # 1. I/Q: each group is [I0, I1, Q0, Q1].
    raw = np.array([3, 4, 5, 6, 7, 8, 9, 10], dtype=np.int16)
    z = np.empty(raw.size // 2, dtype=np.complex128)
    z[0::2] = raw[0::4].astype(float) + 1j * raw[2::4]
    z[1::2] = raw[1::4].astype(float) + 1j * raw[3::4]
    assert np.array_equal(z, [3+5j, 4+6j, 7+9j, 8+10j])

    # xWR14xx four-lane, four-RX, complex I-first example (SWRA581B).
    raw14 = np.array([1, 2, 3, 4, 11, 12, 13, 14], dtype=float)
    words14 = raw14.reshape(-1, 8)
    rx14 = words14[:, :4] + 1j * words14[:, 4:]
    np.testing.assert_array_equal(rx14[0], [1+11j, 2+12j, 3+13j, 4+14j])

    # 2. Eight samples with two phase rotations: FFT peak at k=2.
    tone = np.exp(1j * 2 * np.pi * 2 * np.arange(8) / 8)
    assert np.argmax(np.abs(np.fft.fft(tone))) == 2

    # 3. Project constants, but IDEAL eight-element ULA geometry.
    c, fs, slope = 3e8, 10e6, 29.982e12
    ns, nc, channels, n_angle = 256, 128, 8, 180
    tslow = 480e-6
    wavelength = c / (77e9 + slope * 60e-6 / 2)
    dr = c * fs / (2 * slope * ns)
    dv = wavelength / (2 * nc * tslow)
    kr, kd, qa = 14, 5, 45  # exact DFT grids; qa=45 gives a simple 30 degrees
    truth = [kr * dr, kd * dv, np.degrees(np.arcsin(2 * qa / n_angle))]
    n = np.arange(ns)[:, None, None]
    m = np.arange(nc)[None, :, None]
    p = np.arange(channels)[None, None, :]
    cube = np.exp(1j * 2 * np.pi * (kr * n / ns + kd * m / nc + qa * p / n_angle))
    assert cube.shape == (256, 128, 8)

    # 4. Range FFT along samples.
    wr = np.hamming(ns).reshape(-1, 1, 1)
    range_cube = np.fft.fft(cube * wr, axis=0)
    range_power = np.mean(np.abs(range_cube) ** 2, axis=(1, 2))
    k_range = int(np.argmax(range_power))

    # 5. Doppler FFT along loops, for ALL channels.
    wd = np.hamming(nc).reshape(1, -1, 1)
    doppler_cube = np.fft.fftshift(np.fft.fft(range_cube * wd, axis=1), axes=1)
    velocity_axis = wavelength * np.fft.fftshift(np.fft.fftfreq(nc, d=tslow)) / 2
    k_doppler = int(np.argmax(np.sum(np.abs(doppler_cube[k_range]) ** 2, axis=1)))

    # 6. Spatial FFT, valid only for the ideal calibrated ULA above.
    angle_spectrum = np.fft.fftshift(np.fft.fft(doppler_cube[k_range, k_doppler], n=n_angle))
    q = np.arange(-n_angle // 2, n_angle // 2)
    angle_axis = np.degrees(np.arcsin(2 * q / n_angle))
    k_angle = int(np.argmax(np.abs(angle_spectrum)))
    estimated = [k_range * dr, velocity_axis[k_doppler], angle_axis[k_angle]]
    np.testing.assert_allclose(estimated, truth, atol=1e-10)
    print('range (m), speed (m/s), angle (deg):', np.round(estimated, 6))

    # 7. CFAR on linear power. Neighbouring bins may also be detected.
    detected, threshold = ca_cfar(range_power)
    assert detected[kr]
    print('CFAR selected range bins:', np.flatnonzero(detected).tolist())

    # 8. SEPARATE micro-motion exercise at an already selected target bin.
    time = np.arange(100) * 0.08
    displacement_true = 0.1e-3 * np.sin(2 * np.pi * 0.25 * time)
    trace = np.exp(1j * 4 * np.pi * displacement_true / wavelength)
    phase_unwrapped = np.unwrap(np.angle(trace))
    displacement = wavelength * (phase_unwrapped - phase_unwrapped[0]) / (4 * np.pi)
    np.testing.assert_allclose(displacement, displacement_true, atol=1e-15)
    print('max displacement (mm):', np.max(np.abs(displacement)) * 1000)
    print('All teaching checks passed. No measured data was loaded.')


if __name__ == '__main__':
    main()
