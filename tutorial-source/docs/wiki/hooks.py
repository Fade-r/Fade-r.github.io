"""Generate equation SVGs during every MkDocs build, including local preview."""
from pathlib import Path
import shutil
import subprocess

from mkdocs.exceptions import PluginError


def on_post_build(config):
    tools = Path(__file__).resolve().parent / "tools"
    node = shutil.which("node")
    if not node or not (tools / "node_modules/mathjax-full/package.json").is_file():
        raise PluginError(
            "Equation rendering requires Node.js and locked build dependencies. "
            "Run: npm ci --prefix docs/wiki/tools --ignore-scripts"
        )
    result = subprocess.run(
        [node, str(tools / "render-math.cjs"), str(Path(config["site_dir"]).resolve())],
        cwd=tools, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120, check=False,
    )
    if result.returncode:
        raise PluginError(f"Equation build failed:\n{result.stdout}\n{result.stderr}")
    print(result.stdout.strip())
