% Deterministic FMCW lesson. Base MATLAB, R2016b or newer.
% Ideal 8-element half-wavelength ULA, simultaneous/already compensated.
% No measured input, hardware, network, path changes, or file output.
c = 3e8; fc = 77e9; slope = 30e12; fs = 8e6;
ns = 256; nc = 64; channels = 8; na = 64;
tslow = 1e-3; wavelength = c/fc;
targetRange = 5; fd = 125; targetAngle = 30;
targetVelocity = wavelength*fd/2;
fb = 2*slope*targetRange/c;

n = reshape(0:ns-1,[],1,1);
m = reshape(0:nc-1,1,[],1);
p = reshape(0:channels-1,1,1,[]);
x = exp(1j*(2*pi*fb*n/fs+2*pi*fd*m*tslow+pi*p*sind(targetAngle)));
assert(isequal(size(x),[ns nc channels]));

wr = reshape(0.54-0.46*cos(2*pi*(0:ns-1)/(ns-1)),[],1,1);
rangeCube = fft(x.*wr,ns,1);
wd = reshape(0.54-0.46*cos(2*pi*(0:nc-1)/(nc-1)),1,[],1);
dopplerCube = fftshift(fft(rangeCube.*wd,nc,2),2);
powerMap = sum(abs(dopplerCube).^2,3);
positiveMap = powerMap(1:ns/2,:);
[~, flatIndex] = max(positiveMap(:));
[rangeIndex, speedIndex] = ind2sub(size(positiveMap),flatIndex);
rangeAxis = (0:ns/2-1)*c*fs/(2*slope*ns);
velocityAxis = wavelength*(-nc/2:nc/2-1)/(2*nc*tslow);

z = reshape(dopplerCube(rangeIndex,speedIndex,:),1,[]);
spatial = fftshift(fft(z,na));
q = -na/2:na/2-1;
angleAxis = asind(2*q/na);
[~, angleIndex] = max(abs(spatial));
estimate = [rangeAxis(rangeIndex),velocityAxis(speedIndex),angleAxis(angleIndex)];
assert(max(abs(estimate-[targetRange targetVelocity targetAngle])) < 1e-10);
assert(rangeIndex-1==32 && speedIndex-1-nc/2==8 && q(angleIndex)==16);

distancePower = abs(rangeCube(1:ns/2,1,1)).^2;
[detected,threshold] = ca_cfar(distancePower,8,2,1e-3);
assert(detected(33) && isnan(threshold(1)) && isnan(threshold(end)));
[smallDetected,smallThreshold] = ca_cfar([1 1 2 8 2 1 1],2,1,1/16);
assert(abs(smallThreshold(4)-4)<1e-12 && smallDetected(4));

% Four-RX I-first storage: RX changes fastest inside each sample.
nsTest = 2; loops = 2; ntx = 3; nrx = 4;
raw = 1:nsTest*loops*ntx*nrx*2;
words = reshape(raw,8,[]);
iq = words(1:4,:)+1j*words(5:8,:);
physical = reshape(iq,nrx,nsTest,ntx,loops);
frame = reshape(permute(physical,[2 4 1 3]),nsTest,loops,ntx*nrx);
for sample = 0:nsTest-1
    for loop = 0:loops-1
        for tx = 0:ntx-1
            for rx = 0:nrx-1
                offset = ((loop*ntx+tx)*nsTest+sample)*8;
                expected = offset+rx+1+1j*(offset+rx+5);
                assert(frame(sample+1,loop+1,tx*nrx+rx+1)==expected);
            end
        end
    end
end

offsets = repelem((0:2)'*160e-6,4);
reference = exp(1j*.2*(0:11)');
observed = reference.*exp(1j*2*pi*fd*offsets);
compensated = observed.*exp(-1j*2*pi*fd*offsets);
assert(max(abs(compensated-reference))<1e-14);

time = (0:99)*.08;
displacement = .1e-3*sin(2*pi*.25*time);
trace = exp(1j*4*pi*displacement/wavelength);
phase = unwrap(angle(trace));
recovered = wavelength*(phase-phase(1))/(4*pi);
assert(max(abs(recovered-displacement))<1e-15);
disp('range_m, velocity_mps, angle_deg:');
disp(estimate);
disp('CFAR range bins (zero-based):');
disp((find(detected)-1)');
disp('ADC layout, TDM compensation and phase checks passed.');

function [detected,threshold] = ca_cfar(power,train,guard,pfa)
power = double(power(:));
threshold = nan(size(power));
count = 2*train;
alpha = count*(pfa^(-1/count)-1);
margin = train+guard;
for k = 1+margin:numel(power)-margin
    left = power(k-guard-train:k-guard-1);
    right = power(k+guard+1:k+guard+train);
    threshold(k) = alpha*(sum(left)+sum(right))/count;
end
detected = isfinite(threshold) & power > threshold;
end
