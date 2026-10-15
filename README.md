# 毫米波雷达数据采集与信号处理教程

从回波、ADC 数据和 I/Q 解析开始，逐步学习距离、速度、方向、微位移与目标检测。每一步结合公式、小数值例子和 MATLAB / Python 实现，并说明 IWR1443 与 IWR1843 的相关差异。

## 📚 阅读教程

本分支根目录保存已构建的网站，入口是 `index.html`。在本目录运行：

```bash
python -m http.server 8000 --bind 127.0.0.1
```

然后访问 <http://127.0.0.1:8000/>。公式使用 MathJax CDN，需要联网；其余主要页面资源随站点提供。

GitHub 仓库页面不会直接运行 HTML。是否通过 GitHub Pages 上线，取决于仓库的 Pages 设置；本次更新不改变该设置。

## 📦 源码与复现

| 位置 | 内容 |
| --- | --- |
| [教程正文](tutorial-source/docs/wiki/content/index.md) | Markdown、图片和交互资源 |
| [教学示例](tutorial-source/docs/wiki/examples/) | 可独立运行的 MATLAB / Python 程序 |
| [原处理代码](tutorial-source/project/src/) | 教程分析的两个 Python 文件 |
| [参考索引](tutorial-source/references/README.md) | 上游代码、许可和资料核验记录 |
| [验证脚本](tutorial-source/workbench/experiments/wiki-build/) | 示例、源码摘录和站内链接检查 |

从本仓库根目录运行：

```bash
python -m pip install -r tutorial-source/docs/wiki/requirements.txt
python -m pip install -r tutorial-source/project/requirements.txt
cd tutorial-source
python -m mkdocs build -f docs/wiki/mkdocs.yml --strict --clean
python workbench/experiments/wiki-build/verify_tutorial.py
python workbench/experiments/wiki-build/verify_wiki.py
python docs/wiki/examples/tutorial_pipeline.py
```

MATLAB 中运行 `tutorial-source/docs/wiki/examples/tutorial_pipeline.m`。构建后的网页位于 `tutorial-source/docs/wiki/site/`；发布更新时，将该目录的内容复制到分支根目录，保留 `tutorial-source/` 和本说明。

## 🔍 数据与结果

原始采集 BIN、大型 NPZ 中间数组、第三方 PDF/HTML 缓存和本机工作记录不随分支发布。教学示例使用合成数据，可以直接运行；原处理程序需要自行提供 `tutorial-source/project/data/raw/adc_data.bin`，并核对采集参数。

网页中的实测图片是历史诊断结果，保留用于讲解处理问题，不能作为已经完成硬件标定的证据。具体问题见[结果可信度](tutorial-source/docs/wiki/content/audit/scientific-audit.md)。原处理算法保持不变，教学实现与实际采集格式的区别在各章说明。

上游 MATLAB 参考文件保留原 MIT 许可；TI、PySDR 等资料仅提供来源链接与核验记录，未重新分发其 PDF 或网页。
