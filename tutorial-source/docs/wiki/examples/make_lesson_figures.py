"""Generate deterministic teaching figures from stated analytic signals.

No measured data is read. SVGs and CSV source values go to assets/lessons.
PNG review copies go to workbench/cache/wiki-rebuild. Existing outputs with
these exact names are regenerated. Run with the radar-env Python interpreter.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/wiki/content/assets/lessons'
REVIEW = ROOT / 'workbench/cache/wiki-rebuild'
BLUE, ORANGE = '#0072B2', '#B84E00'


def export(name, fig, columns, header):
    OUT.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / (name+'.svg'), facecolor='white')
    fig.savefig(REVIEW / (name+'.png'), dpi=130, facecolor='white')
    np.savetxt(OUT / (name+'.csv'), np.column_stack(columns),
               delimiter=',', header=header, comments='')
    plt.close(fig)


def axes(ylabel, xlabel, size=(8, 3.6)):
    fig, ax = plt.subplots(figsize=size, layout='constrained')
    ax.set(xlabel=xlabel, ylabel=ylabel)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(alpha=.2)
    return fig, ax


def main():
    with plt.rc_context({'font.family': 'Microsoft YaHei', 'font.size': 12,
                         'axes.unicode_minus': False, 'svg.fonttype': 'path',
                         'lines.linewidth': 2}):
        t = np.linspace(0, 40, 101)
        f = 77 + .03*t
        fig, ax = axes('发射频率 / GHz', '时间 / µs')
        ax.plot(t, f, color=BLUE)
        ax.plot([0, 40], [77, 78.2], 'o', color=BLUE)
        ax.set(xticks=[0,10,20,30,40], yticks=[77,77.3,77.6,77.9,78.2])
        export('chirp-frequency', fig, [t, f], 'time_us,frequency_GHz')

        t = np.linspace(0, .4, 401)
        tx = 30*t
        rx = np.where(t >= .1, 30*(t-.1), np.nan)
        fig, ax = axes('相对 77 GHz 的频率增量 / MHz', '时间 / µs')
        ax.plot(t, tx, color=BLUE, label='发射信号')
        ax.plot(t, rx, '--', color=ORANGE, label='回波：延迟 0.1 µs')
        ax.annotate('', xy=(.3,9), xytext=(.3,6),
                    arrowprops={'arrowstyle':'<->','color':'#222222'})
        ax.text(.31,7.5,'3 MHz', va='center')
        ax.legend(loc='upper left')
        export('echo-frequency', fig, [t,tx,rx], 'time_us,tx_offset_MHz,rx_offset_MHz')

        t = np.linspace(0, 2, 801)
        n = np.arange(16)/8
        fig, ax = axes('归一化幅度', '时间 / µs')
        ax.plot(t, np.cos(2*np.pi*t), color=BLUE, label='I = cos(2πft)')
        ax.plot(t, np.sin(2*np.pi*t), '--', color=ORANGE, label='Q = sin(2πft)')
        ax.plot(n,np.cos(2*np.pi*n),'o', color=BLUE)
        ax.plot(n,np.sin(2*np.pi*n),'s', color=ORANGE)
        ax.legend(loc='upper right', ncol=2)
        ax.set(ylim=(-1.35,1.65))
        export('iq-sampling',fig,[n,np.cos(2*np.pi*n),np.sin(2*np.pi*n)],'time_us,I,Q')

        n = np.arange(8)
        a = np.abs(np.fft.fft(np.exp(1j*2*np.pi*2*n/8)))
        fig, ax = axes('FFT 幅度', '频率格 k（从 0 编号）')
        ax.vlines(n,0,a,color=BLUE); ax.plot(n,a,'o',color=BLUE)
        ax.set(xticks=n,ylim=(0,9))
        export('fft-eight',fig,[n,a],'bin,amplitude')

        ns, fs, slope, c = 256, 8e6, 30e12, 3e8
        n = np.arange(ns)
        z = np.exp(1j*2*np.pi*1e6*n/fs)
        spec = np.abs(np.fft.fft(z))/ns
        r = np.arange(ns//2)*c*fs/(2*slope*ns)
        fig, ax = axes('幅度 / 采样点数', '距离 / m')
        ax.plot(r,spec[:ns//2],color=BLUE)
        ax.set(xlim=(0,10),ylim=(0,1.1))
        ax.annotate('5 m',xy=(5,1),xytext=(6.2,.8),arrowprops={'arrowstyle':'->'})
        export('range-peak',fig,[r,spec[:ns//2]],'range_m,amplitude_over_N')

        nc, ts, lam = 64, 1e-3, c/77e9
        z = np.exp(1j*2*np.pi*125*np.arange(nc)*ts)
        s = np.abs(np.fft.fftshift(np.fft.fft(z)))/nc
        v = lam*np.fft.fftshift(np.fft.fftfreq(nc,ts))/2
        fig, ax = axes('幅度 / 观测次数', '径向速度 / (m/s)')
        ax.plot(v,s,color=BLUE)
        ax.set(ylim=(0,1.1))
        ax.annotate('约 0.244 m/s',xy=(lam*125/2,1),xytext=(.42,.8),arrowprops={'arrowstyle':'->'})
        export('doppler-peak',fig,[v,s],'velocity_mps,amplitude_over_N')

        p=np.arange(8); z=np.exp(1j*np.pi*p*.5)
        q=np.arange(-32,32); u=2*q/64
        theta=np.degrees(np.arcsin(u))
        s=np.abs(np.fft.fftshift(np.fft.fft(z,64)))/8
        fig, ax = axes('幅度 / 通道数', '角度 / °')
        ax.plot(theta,s,color=BLUE); ax.set(ylim=(0,1.1),xlim=(-90,90))
        ax.annotate('30°',xy=(30,1),xytext=(48,.8),arrowprops={'arrowstyle':'->'})
        export('angle-peak',fig,[theta,s],'angle_deg,amplitude_over_P')

        t=np.arange(100)*.08; displacement=.1*np.sin(2*np.pi*.25*t)
        phase=4*np.pi*(displacement*1e-3)/lam
        fig, axs=plt.subplots(2,1,figsize=(8,4.6),layout='constrained',sharex=True)
        axs[0].plot(t,phase,color=BLUE); axs[0].set(ylabel='相位变化 / rad')
        axs[1].plot(t,displacement,'--',color=ORANGE); axs[1].set(ylabel='位移 / mm',xlabel='时间 / s')
        for ax in axs: ax.grid(alpha=.2); ax.spines[['top','right']].set_visible(False)
        export('phase-displacement',fig,[t,phase,displacement],'time_s,phase_rad,displacement_mm')
    print('Generated 8 analytic figures and their CSV data.')


if __name__ == '__main__':
    main()
