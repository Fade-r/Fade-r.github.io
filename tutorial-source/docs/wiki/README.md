# 毫米波雷达教程

MkDocs Material 源码位于 `content/`，静态网页位于 `site/`。正式处理代码与实测数据保留在 `project/`，本轮教学重构没有修改它们。

## 阅读顺序

简介 → 发射信号 → 回波与混频 → I/Q 与采样 → 硬件采集 → 帧与数组 → ADC 读取 → FFT → 距离 → 速度 → 检测 → 角度 → 微位移 → 完整示例。

MATLAB 和 Python 实现随各步骤提供。原程序的函数说明、参数、历史输出和诊断集中在“项目案例”。

## 本地预览

从项目根目录运行：

```powershell
conda run -n radar-env python -m mkdocs serve -f docs/wiki/mkdocs.yml -a 127.0.0.1:8000
```

打开 http://127.0.0.1:8000/ ，用 Ctrl+C 停止服务。数学公式使用固定版本的 MathJax CDN，需要网络；其他站点资源均保存在本地。

## 构建与验证

```powershell
conda run -n radar-env python -m mkdocs build -f docs/wiki/mkdocs.yml --strict --clean
conda run -n radar-env python docs/wiki/examples/tutorial_pipeline.py
conda run -n radar-env python workbench/experiments/wiki-build/verify_tutorial.py
conda run -n radar-env python workbench/experiments/wiki-build/verify_wiki.py
node workbench/experiments/wiki-build/verify_signal_labs.cjs
```

检查包括 Python 示例语法、源码摘录、下载副本一致性、本地链接和资源，以及首页与左侧目录的分组、标题、顺序和链接一致性。交互模型用 Node.js 检查全部预设距离、采样点、矩阵索引和 DFT 行；按钮、播放和主题还需在浏览器检查。MATLAB 新版脚本尚未实际运行，不能把静态或 Python 检查视为 MATLAB 验证。

## 文件维护

- `examples/tutorial_pipeline.py` 与 `.m`：完整教学代码；网页下载副本位于 `content/assets/downloads/`，修改后须同步。
- `examples/make_lesson_figures.py`：生成解析信号教学图与对应 CSV，输出到 `content/assets/lessons/`；预览 PNG 位于 `workbench/cache/wiki-rebuild/`。
- `content/assets/figures/`：原项目诊断图快照，与理想信号教学图分开。
- `content/assets/javascripts/signal-labs.js`：回波延迟、I/Q 逐点播放、数据重排、DFT 矩阵演示。模型与页面渲染分开，图形使用当前模型值；不自动播放、不循环，页面隐藏时暂停。系统要求减少动态效果时只保留手动步进。
- `workbench/archive/wiki-before-runoob-20261015/`：重构前的内容、示例和配置归档。
- `references/tutorial-writing.md`：教学写法参考记录。

每次修改完成并检查通过后，同步构建网站与教学源码，推送至 `Fade-r/Fade-r.github.io` 的 `IWR1443-Signal-Processing` 分支。发布时不包含原始采集数据、本机缓存和临时工作记录。
