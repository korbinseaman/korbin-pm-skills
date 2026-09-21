from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import matplotlib
from matplotlib import font_manager

DEFAULT_DPI = 180
DEFAULT_FIGSIZE = (10, 7)
RADAR_FIGSIZE = (9, 9)


def configure_fonts():
    """优先使用本机已安装的 CJK 字体，不在 Skill 中打包字体文件。"""
    candidates = [
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "Microsoft YaHei",
        "PingFang SC",
        "SimHei",
        "Arial Unicode MS",
    ]

    # Fontconfig 可以找到 Matplotlib 初始字体缓存可能遗漏的 TTC/OTC 字体。
    if shutil.which("fc-match"):
        for family in candidates:
            try:
                path = subprocess.check_output(
                    ["fc-match", "-f", "%{file}", family], text=True, stderr=subprocess.DEVNULL
                ).strip()
            except Exception:
                path = ""
            if path and Path(path).exists():
                try:
                    font_manager.fontManager.addfont(path)
                    name = font_manager.FontProperties(fname=path).get_name()
                    matplotlib.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
                    matplotlib.rcParams["axes.unicode_minus"] = False
                    return name
                except Exception:
                    pass

    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((name for name in candidates if name in available), "DejaVu Sans")
    matplotlib.rcParams["font.sans-serif"] = [chosen, "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    return chosen


def ensure_output_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
