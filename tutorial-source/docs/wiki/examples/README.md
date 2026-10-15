# MATLAB / Python 教学程序

`tutorial_pipeline.py` 与 `tutorial_pipeline.m` 按相同顺序实现 I/Q 配对、小型 FFT、单目标模拟、距离/速度/角度 FFT、一维 CFAR 和独立微位移练习。各步解释及对应代码直接放在 Wiki 的相关章节；完整文件用于最后的综合练习。

程序使用理想半波长均匀线阵，不读取实测文件。IWR1443 官方四 lane 配对与项目四整数配对分别用小数组验证，不能互相替换。

网页下载副本在 `../content/assets/downloads/`，更新源文件后同步复制。运行前后的断言用于验证教学例子，不代表实测硬件已标定。
