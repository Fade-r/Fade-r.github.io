"""Deterministic FMCW teaching example; no measured files or hardware access.

Ideal eight-element half-wavelength ULA, simultaneous observation or already
motion-compensated channels. This is not either TI board's physical layout.
The sampled signal uses the narrowband, separable range/Doppler model.
"""
import numpy as np


def ca_cfar(power, train=8, guard=2, pfa=1e-3):
    power = np.asarray(power, dtype=float)
    threshold = np.full(power.size, np.nan)
    count = 2*train
    alpha = count*(pfa**(-1/count)-1)
    margin = train+guard
    for k in range(margin, power.size-margin):
        left = power[k-guard-train:k-guard]
        right = power[k+guard+1:k+guard+train+1]
        threshold[k] = alpha*(left.sum()+right.sum())/count
    return np.isfinite(threshold) & (power > threshold), threshold


def main():
    c, fc, slope, fs = 3e8, 77e9, 30e12, 8e6
    ns, nc, channels, na = 256, 64, 8, 64
    tslow = 1e-3
    wavelength = c/fc
    target_range, fd, target_angle = 5.0, 125.0, 30.0
    target_velocity = wavelength*fd/2
    fb = 2*slope*target_range/c

    # Axes: ADC sample, repeated observation, ideal spatial channel.
    n = np.arange(ns)[:, None, None]
    m = np.arange(nc)[None, :, None]
    p = np.arange(channels)[None, None, :]
    x = np.exp(1j*(2*np.pi*fb*n/fs + 2*np.pi*fd*m*tslow
                   + np.pi*p*np.sin(np.deg2rad(target_angle))))
    assert x.shape == (ns, nc, channels)

    wr = np.hamming(ns).reshape(ns, 1, 1)
    range_cube = np.fft.fft(x*wr, axis=0)
    wd = np.hamming(nc).reshape(1, nc, 1)
    doppler_cube = np.fft.fftshift(
        np.fft.fft(range_cube*wd, axis=1), axes=1)
    power_map = np.sum(np.abs(doppler_cube)**2, axis=2)

    # One target is assumed: choose the strongest positive-range RD cell.
    k, ell_index = np.unravel_index(
        np.argmax(power_map[:ns//2]), power_map[:ns//2].shape)
    range_axis = np.arange(ns//2)*c*fs/(2*slope*ns)
    velocity_axis = wavelength*np.fft.fftshift(
        np.fft.fftfreq(nc, d=tslow))/2

    z = doppler_cube[k, ell_index, :]
    spatial = np.fft.fftshift(np.fft.fft(z, n=na))
    q = np.arange(-na//2, na//2)
    angle_axis = np.degrees(np.arcsin(2*q/na))
    angle_index = np.argmax(np.abs(spatial))
    estimate = np.array([range_axis[k], velocity_axis[ell_index],
                         angle_axis[angle_index]])
    np.testing.assert_allclose(
        estimate, [target_range, target_velocity, target_angle], atol=1e-10)
    assert k == 32 and ell_index-nc//2 == 8 and q[angle_index] == 16

    # Separate 1-D CFAR exercise on a single-channel distance power profile.
    distance_power = np.abs(range_cube[:ns//2, 0, 0])**2
    detected, threshold = ca_cfar(distance_power)
    assert detected[32]
    assert np.isnan(threshold[0]) and np.isnan(threshold[-1])
    small = np.array([1, 1, 2, 8, 2, 1, 1], dtype=float)
    small_detected, small_threshold = ca_cfar(small, 2, 1, 1/16)
    assert np.isclose(small_threshold[3], 4) and small_detected[3]

    # Independent xWR14xx four-RX, I-first pairing and complete index test.
    ns_test, loops, ntx, nrx = 2, 2, 3, 4
    raw = np.arange(1, ns_test*loops*ntx*nrx*2+1, dtype=float)
    words = raw.reshape(-1, 8)
    iq = words[:, :4]+1j*words[:, 4:]
    physical = iq.reshape(loops, ntx, ns_test, nrx)
    frame = physical.transpose(2, 0, 1, 3).reshape(ns_test, loops, ntx*nrx)
    for sample in range(ns_test):
        for loop in range(loops):
            for tx in range(ntx):
                for rx in range(nrx):
                    offset = ((loop*ntx+tx)*ns_test+sample)*8
                    expected = offset+rx+1 + 1j*(offset+rx+5)
                    assert frame[sample, loop, tx*nrx+rx] == expected

    # Independent TDM phase compensation test, positive Doppler convention.
    offsets = np.repeat(np.arange(3)*160e-6, 4)
    reference = np.exp(1j*.2*np.arange(12))
    observed = reference*np.exp(1j*2*np.pi*fd*offsets)
    compensated = observed*np.exp(-1j*2*np.pi*fd*offsets)
    np.testing.assert_allclose(compensated, reference, atol=1e-14)

    # Separate micro-motion target, sampled once per frame.
    time = np.arange(100)*.08
    displacement = .1e-3*np.sin(2*np.pi*.25*time)
    trace = np.exp(1j*4*np.pi*displacement/wavelength)
    phase = np.unwrap(np.angle(trace))
    recovered = wavelength*(phase-phase[0])/(4*np.pi)
    np.testing.assert_allclose(recovered, displacement, atol=1e-15)
    print("range_m, velocity_mps, angle_deg:", np.round(estimate, 6))
    print("CFAR range bins:", np.flatnonzero(detected).tolist())
    print("ADC layout, TDM compensation and phase tests passed.")
    print("No measured data was read or modified.")


if __name__ == "__main__":
    main()
