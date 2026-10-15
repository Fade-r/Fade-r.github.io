%% Ideal point target and calibrated half-wave ULA, NOT measured IWR1443 data.
% Channels are simultaneous or already TDM-compensated. No input files.
clear; clc;

%% 1. I/Q groups: [I0 I1 Q0 Q1].
raw = double(int16([3 4 5 6 7 8 9 10]));
z = complex(zeros(1, numel(raw)/2));
z(1:2:end) = raw(1:4:end) + 1j*raw(3:4:end);
z(2:2:end) = raw(2:4:end) + 1j*raw(4:4:end);
assert(isequal(z, [3+5j 4+6j 7+9j 8+10j]));

% xWR14xx four-lane, four-RX, complex I-first example (SWRA581B).
raw14 = [1 2 3 4 11 12 13 14];
words14 = reshape(raw14,8,[]);
rx14 = words14(1:4,:) + 1j*words14(5:8,:);
assert(isequal(rx14,[1+11j;2+12j;3+13j;4+14j]));

%% 2. Two phase rotations in eight samples: zero-based FFT bin 2.
tone = exp(1j*2*pi*2*(0:7)/8);
[~, peak] = max(abs(fft(tone)));
assert(peak-1 == 2);

%% 3. Project constants, but IDEAL eight-element ULA geometry.
c = 3e8; fs = 10e6; slope = 29.982e12;
ns = 256; nc = 128; channels = 8; nAngle = 180;
tslow = 480e-6;
wavelength = c/(77e9 + slope*60e-6/2);
dr = c*fs/(2*slope*ns);
dv = wavelength/(2*nc*tslow);
kr = 14; kd = 5; qa = 45; % spatial bin 45 gives 30 degrees
truth = [kr*dr, kd*dv, asind(2*qa/nAngle)];
n = reshape(0:ns-1, [], 1, 1);
m = reshape(0:nc-1, 1, [], 1);
p = reshape(0:channels-1, 1, 1, []);
cube = exp(1j*2*pi*(kr*n/ns + kd*m/nc + qa*p/nAngle));
assert(isequal(size(cube), [256 128 8])); % implicit expansion, R2016b+

%% 4. Range FFT, dimension 1; symmetric Hamming window without toolbox.
wr = reshape(0.54-0.46*cos(2*pi*(0:ns-1)/(ns-1)), [], 1, 1);
rangeCube = fft(cube.*wr, ns, 1);
rangePower = squeeze(mean(mean(abs(rangeCube).^2, 3), 2));
[~, kRange] = max(rangePower);

%% 5. Doppler FFT, dimension 2, for ALL channels.
wd = reshape(0.54-0.46*cos(2*pi*(0:nc-1)/(nc-1)), 1, [], 1);
dopplerCube = fftshift(fft(rangeCube.*wd, nc, 2), 2);
velocityAxis = wavelength*(-nc/2:nc/2-1)/(2*nc*tslow);
[~, kDoppler] = max(sum(abs(dopplerCube(kRange,:,:)).^2, 3));

%% 6. Spatial FFT, calibrated half-wave ULA assumed.
spatial = squeeze(dopplerCube(kRange,kDoppler,:));
angleSpectrum = fftshift(fft(spatial, nAngle));
q = -nAngle/2:nAngle/2-1;
angleAxis = asind(2*q/nAngle);
[~, kAngle] = max(abs(angleSpectrum));
estimated = [(kRange-1)*dr, velocityAxis(kDoppler), angleAxis(kAngle)];
assert(max(abs(estimated-truth)) < 1e-10);
disp('range (m), speed (m/s), angle (deg):'); disp(estimated);

%% 7. CFAR: linear power, skip edges, no wrap-around.
[detected, threshold] = ca_cfar(rangePower, 8, 2, 1e-3);
assert(detected(kr+1));
disp('CFAR selected zero-based range bins:'); disp(find(detected)'-1);

%% 8. Separate noise-free micro-motion example, at an already selected bin.
time = (0:99)*0.08;
displacementTrue = 0.1e-3*sin(2*pi*0.25*time);
trace = exp(1j*4*pi*displacementTrue/wavelength);
phaseUnwrapped = unwrap(angle(trace));
displacement = wavelength*(phaseUnwrapped-phaseUnwrapped(1))/(4*pi);
assert(max(abs(displacement-displacementTrue)) < 1e-15);
fprintf('max displacement (mm): %.6f\n', max(abs(displacement))*1000);
disp('All teaching checks passed. No measured data was loaded.');

function [detected, threshold] = ca_cfar(power, training, guard, pfa)
    count = 2*training;
    alpha = count*(pfa^(-1/count)-1);
    threshold = nan(size(power));
    detected = false(size(power));
    for k = training+guard+1:numel(power)-training-guard
        left = power(k-guard-training:k-guard-1);
        right = power(k+guard+1:k+guard+training);
        noise = mean([left(:); right(:)]);
        threshold(k) = alpha*noise;
        detected(k) = power(k) > threshold(k);
    end
end
