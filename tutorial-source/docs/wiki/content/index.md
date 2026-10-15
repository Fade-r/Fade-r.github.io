# 从采集到结果，学会处理毫米波雷达数据

你采集的 `adc_data.bin` 里还没有距离、速度或角度，只有一长串整数。这个项目用 Python 把整数还原成复数信号，再用 FFT 分析目标可能在多远、怎样运动，并尝试从相位变化中提取微小位移。

教程以这份 IWR1443 项目为实例；IWR1843 用户可按同一流程学习，设备差异在对应步骤提示。先从[雷达、DCA1000 和文件之间的关系](data/capture.md)开始，再沿着数据逐步往下处理。

先顺着下面这张图读一遍。**距离、速度和角度都用到 FFT，但取的是不同方向的数据。**

<ol class="walkthrough">
<li><strong>把整数配成 I、Q</strong><p>例如四个数 [3, 4, 5, 6]，按教程的排列约定组成 3+5j、4+6j。一个复数同时保留幅度和相位。</p><a href="data/adc-iq-layout.html">看 I/Q 配对和数组重排 →</a></li>
<li><strong>在一次扫频里看变化：求距离</strong><p>取同一通道、同一次扫频的 256 个采样点。分析它们振荡得有多快，把频率换算成距离。</p><a href="processing/range.html">看距离 FFT →</a></li>
<li><strong>在多次扫频之间看变化：求速度</strong><p>固定一个距离格和一个通道，比较 128 次观测的相位。相位变化越快，对应的径向速度通常越大。</p><a href="processing/doppler.html">看多普勒 FFT →</a></li>
<li><strong>在不同天线之间看差别：求方向</strong><p>固定距离和速度，比较天线之间的相位差。还需要知道天线的位置和排列顺序，才能换成角度。</p><a href="processing/angle.html">看角度 FFT →</a></li>
</ol>

距离 FFT 后还有另一条分支：选定目标所在的距离格，持续记录它的复数值，用相位变化估计微位移。它不需要先经过角度 FFT。[看相位与位移](processing/phase.md)。

## 第一次读，从这里开始

[从数据采集开始](data/capture.md){ .md-button .md-button--primary }

[动手比较三个数值例子](orientation/parameters-and-shapes.md#hands-on){ .md-button }

不熟悉术语时，只记住：**chirp 是一次扫频；sample 是其中一个采样点；bin 是 FFT 输出的一格；shape 是数组各维的长度。** 文中的英文保留给你对照代码，解释以中文为主。

从[数据采集](data/capture.md)开始，接着读[一帧数据](orientation/learning-path.md)、[复数与 FFT](foundations/signal-and-fft.md)，再沿上面的步骤处理文件。每一步都在本页解释理论、展示 Python 与 MATLAB 实现并检查输出。完成后用[综合练习](practice/end-to-end.md)把各步连起来复核。

## 这份项目目前做到哪了

项目已能读取数据、计算频谱并输出 13 张诊断图。按代码中 3 发射、4 接收、每帧 128 轮的配置，文件长度恰好对应 100 帧；完整采集配置还没有归档，数据的排列方式仍需核实。

当前默认的 `strict_matlab` 表示“沿用 MATLAB 教程的处理方式”。另一种排列方式 `tdm_candidate` 在已有检查中表现更好，但程序还没有用它生成正式输出。教程里会把这两种方式放在一起解释。

现有结果有三个具体问题：距离谱出现周期重复峰；多普勒只处理了 12 个通道中的 4 个；用于微位移分析的第 30 个距离格信号很弱。因此，这些图适合用来学习和排查代码，暂时不能据此报告目标的角度或位移。[查看问题和对应代码](audit/scientific-audit.md)。

## 想找某一部分

| 你想弄清什么 | 从哪一页读 |
| --- | --- |
| 一帧为什么是 256 × 128 × 12？ | [参数和数组尺寸](orientation/parameters-and-shapes.md) |
| `reshape`、`transpose`、`axis` 怎样用？ | [读取 I/Q](data/adc-iq-layout.md) → [距离 FFT](processing/range.md) |
| 两个 Python 文件怎样配合？ | [代码导读](code/code-map.md) |
| 已有图片的横纵轴是什么？ | [逐张读图](reference/figure-atlas.md) |
| 怎么检验处理结果是否正确？ | [标定实验](audit/validation-roadmap.md) |
| MATLAB 代码来自哪里？ | [代码来源和参考资料](reference/sources.md) |

## 运行项目

在项目根目录执行：

```powershell
conda run -n radar-env python project\src\process_iwr1443_adc.py
```

输出保存在 `project/outputs/`。运行会重新生成结果；只阅读本站不需要运行雷达处理程序。
