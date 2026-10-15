# IWR1443 科研 Wiki

该目录保存 MkDocs Material 源站点和构建产物。雷达运行代码仍位于 `project/src/`，原始数据仍位于 `project/data/raw/`。

## 本地预览

从项目根目录运行：

```powershell
conda run -n radar-env python -m mkdocs serve -f docs\wiki\mkdocs.yml -a 127.0.0.1:8000
```

打开 `http://127.0.0.1:8000/`。停止服务使用 `Ctrl+C`。

## 严格构建

```powershell
conda run -n radar-env python -m mkdocs build -f docs\wiki\mkdocs.yml --strict --clean
```

构建入口为 `site/index.html`。搜索、导航、代码、图片与参数实验均为站点本地资源；公式当前使用固定版本的 MathJax CDN。使用本地 HTTP 服务可获得完整行为，直接双击 HTML 仅适合作为降级阅读方式；完全断网归档时应再 vendor MathJax。

日间/夜间主题已通过本地 HTTP 交互检查。站点也为直接 `file://` 打开时的存储访问增加了安全包装；自动化浏览器限制了该协议，因此没有把它计入浏览器实测通过范围。

## 内容同步

- `content/assets/figures/` 是 `project/outputs/figures/` 的文档快照；图注必须保留 strict/诊断语境。
- 参数页改用站内的三个手动实验，解释距离、时间间隔和相位位移；不再嵌入旧的动画页面。旧文件保留用于追溯。
- `examples/` 保存 MATLAB 与 Python 可运行教学源程序，`content/assets/downloads/` 为网页下载副本。改动后同步副本并重新运行两种语言。
- 公式、代码行号和 shape 变更后，应重新执行严格构建与浏览器验收。

## 教程阅读顺序

一帧数据 → 复数、采样和 FFT → I/Q 解析 → 距离 → 速度 → 方向 → 微位移 → 检测 → 综合练习 → 实测验证。MATLAB/Python 的实现随各步提供，语法速查与项目函数索引只作辅助查阅。

每个主要步骤同时提供理论说明、两种语言的代码和检查点。`project/src/` 保留原处理行为；教学代码的改进和理想化假设在正文中单独说明。
