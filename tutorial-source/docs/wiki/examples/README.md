# MATLAB / Python 教学程序

`tutorial_pipeline.py` 与 `tutorial_pipeline.m` 使用相同参数，完成单目标模拟、距离/速度/角度 FFT、一维 CA-CFAR，以及独立的 ADC 排列、TDM 补偿和微位移测试。各步骤的原理与短代码放在对应章节。

主例设置目标距离 5 m、多普勒频率 125 Hz、方向 30°；77 GHz 载频对应速度约 0.244 m/s。阵列是理想的八阵元半波长均匀线阵，不是某块 TI 开发板的天线布局。

ADC 测试使用 xWR14xx 四 RX、复数 I-first 八元组排列。程序不读取实测数据，不修改项目处理代码。

## 运行

在项目根目录执行：

```powershell
conda run -n radar-env python docs/wiki/examples/tutorial_pipeline.py
```

MATLAB 中可打开 `tutorial_pipeline.m` 执行。新版 Python 已通过运行测试，MATLAB 版本尚未实际运行。

网页下载副本在 `../content/assets/downloads/`，修改源文件后须同步。

## 教学图

`make_lesson_figures.py` 根据解析公式生成 8 张 SVG 和对应 CSV：

```powershell
conda run -n radar-env python docs/wiki/examples/make_lesson_figures.py
```

正式输出位于 `content/assets/lessons/`；PNG 检查图位于 `workbench/cache/wiki-rebuild/`。这些是模拟信号图，实测诊断图另存于 `content/assets/figures/`。
