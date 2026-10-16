# 毫米波雷达教程

MkDocs Material 源码位于 `content/`，静态网页位于 `site/`。正式处理代码与实测数据保留在 `project/`，本轮教学重构没有修改它们。

## 阅读顺序

简介 → 发射信号 → 回波与混频 → I/Q 与采样 → 硬件采集 → 帧与数组 → ADC 读取 → FFT → 距离 → 速度 → 检测 → 角度 → 微位移 → 完整示例。

MATLAB 和 Python 实现随各步骤提供。原程序的函数说明、参数、历史输出和诊断集中在“项目案例”。

## 本地预览

从项目根目录运行：

```powershell
npm ci --prefix docs/wiki/tools --ignore-scripts
conda run -n radar-env python -m mkdocs serve -f docs/wiki/mkdocs.yml -a 127.0.0.1:8000
```

打开 http://127.0.0.1:8000/ ，用 Ctrl+C 停止服务。安装构建依赖需要网络，阅读已构建网页不再依赖第三方 CDN。公式在构建时转换为内嵌 SVG，禁用 JavaScript 仍可阅读；长公式可在公式区域横向滚动。

构建环境需要 Node.js（本次使用 24.15.0）与现有 Python/MkDocs 环境。Node.js 仅用于网站构建，不改变教程中的 MATLAB/Python 实现。依赖版本保存在 `tools/package-lock.json`，`node_modules/` 不提交、不发布。自定义样式与脚本的链接带内容哈希，更新网页时会自动加载匹配版本，避免旧缓存与新公式混用。

## 构建与验证

```powershell
conda run -n radar-env python -m mkdocs build -f docs/wiki/mkdocs.yml --strict --clean
conda run -n radar-env python docs/wiki/examples/tutorial_pipeline.py
conda run -n radar-env python workbench/experiments/wiki-build/verify_tutorial.py
conda run -n radar-env python workbench/experiments/wiki-build/verify_wiki.py
node workbench/experiments/wiki-build/verify_signal_labs.cjs
node workbench/experiments/wiki-build/verify_lab_fallbacks.cjs
node workbench/experiments/wiki-build/verify_static_math.cjs
conda run -n radar-env python workbench/experiments/wiki-build/verify_static_site.py
```

检查包括 Python 示例语法、源码摘录、下载副本一致性、本地链接和资源，以及首页与左侧目录的分组、标题、顺序和链接一致性。交互模型用 Node.js 检查全部预设距离、采样点、矩阵索引和 DFT 行；按钮、播放和主题还需在浏览器检查。MATLAB 新版脚本尚未实际运行，不能把静态或 Python 检查视为 MATLAB 验证。

`verify_static_site.py` 检查每个公式均含 SVG 和辅助 MathML、SVG 引用完整、页面不加载远程资源。兼容性复测时，在 320 像素浅色和 390 像素深色视口逐页检查，再实际操作目录、搜索、长公式滚动与四个演示。运行 `serve_no_scripts.py` 可在 `http://127.0.0.1:8766/` 检查禁止脚本、字体和数据请求时的正文与公式；此测试服务器只监听本机，不用于发布。

## 文件维护

- 跨页或相距较远的推导，在新公式前用 `!!! formula-recap "具体公式名"` 重现必要前式、符号含义及来源链接；提示默认展开，不能只有“见前文”。解释限制时交代原因与实际处理对象，避免留下只有“不是、不能”的结论。
- 示例切换点数、数组方向或符号含义时就地说明；可顺序运行的代码须验证前一段变量不会影响后一段。`verify_tutorial.py` 检查公式提示生成、FFT 全页 Python 片段顺序运行及关键数值关系。
- `examples/tutorial_pipeline.py` 与 `.m`：完整教学代码；网页下载副本位于 `content/assets/downloads/`，修改后须同步。
- `examples/make_lesson_figures.py`：生成解析信号教学图与对应 CSV，输出到 `content/assets/lessons/`；预览 PNG 位于 `workbench/cache/wiki-rebuild/`。
- `content/assets/figures/`：原项目诊断图快照，与理想信号教学图分开。
- `content/assets/javascripts/signal-labs.js`：回波延迟、I/Q 逐点播放、数据重排、DFT 矩阵演示。模型与页面渲染分开，图形使用当前模型值；不自动播放、不循环，页面隐藏时暂停。系统要求减少动态效果时只保留手动步进。
- `hooks.py` 与 `tools/render-math.cjs`：MkDocs 构建结束时转换全部公式，生成 SVG 样式与辅助 MathML；遇到非法公式立即中止构建。修改公式后运行干净构建，不单独重复执行转换器。
- `workbench/archive/wiki-before-runoob-20261015/`：重构前的内容、示例和配置归档。
- `references/tutorial-writing.md`：教学写法参考记录。

每次修改完成并检查通过后，同步构建网站与教学源码，推送至 `Fade-r/Fade-r.github.io` 的 `IWR1443-Signal-Processing` 分支。发布时不包含原始采集数据、本机缓存和临时工作记录。
