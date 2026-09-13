#!/usr/bin/env python3
"""根据可编辑 CSV 数据重新生成雷达图、四象限图和矩阵定位图。

示例：
  python generate_charts.py --input radar.csv --type radar --output-dir out
  python generate_charts.py --input xy.csv --type quadrant --output-dir out
  python generate_charts.py --input xy.csv --type matrix --output-dir out
  python generate_charts.py --input radar.csv --xy-input xy.csv --type all --output-dir out
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from chart_config import DEFAULT_DPI, DEFAULT_FIGSIZE, RADAR_FIGSIZE, configure_fonts, ensure_output_dir


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "competitor" not in df.columns:
        raise ValueError(f"{path}: 缺少必填列 'competitor'")
    return df


def numeric_dimension_columns(df: pd.DataFrame):
    ignored = {"competitor", "manual_confirmation", "x_label", "y_label", "bubble", "x", "y"}
    cols = []
    for c in df.columns:
        if c in ignored:
            continue
        converted = pd.to_numeric(df[c], errors="coerce")
        if converted.notna().all():
            cols.append(c)
    return cols


def radar(df: pd.DataFrame, out: Path, title: str | None = None):
    dims = numeric_dimension_columns(df)
    if len(dims) < 3:
        raise ValueError("雷达图至少需要 3 个数值评分维度")

    angles = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=RADAR_FIGSIZE, subplot_kw={"polar": True})
    for _, row in df.iterrows():
        values = [float(row[d]) for d in dims]
        values += values[:1]
        ax.plot(angles, values, linewidth=1.8, label=str(row["competitor"]))
        ax.fill(angles, values, alpha=0.06)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dims)
    observed_max = max(float(pd.to_numeric(df[d]).max()) for d in dims)
    ax.set_ylim(0, max(5.0, observed_max))
    ax.set_title(title or "竞品能力雷达图", pad=24)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.12))
    fig.tight_layout()
    path = out / "radar.png"
    fig.savefig(path, dpi=DEFAULT_DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def _xy_labels(df: pd.DataFrame):
    x_label = "X"
    y_label = "Y"
    if "x_label" in df.columns and df["x_label"].notna().any():
        x_label = str(df["x_label"].dropna().iloc[0])
    if "y_label" in df.columns and df["y_label"].notna().any():
        y_label = str(df["y_label"].dropna().iloc[0])
    return x_label, y_label


def _validate_xy(df: pd.DataFrame):
    for c in ("x", "y"):
        if c not in df.columns:
            raise ValueError(f"XY 图表缺少必填列 '{c}'")
        df[c] = pd.to_numeric(df[c], errors="raise")


def quadrant(df: pd.DataFrame, out: Path, title: str | None = None):
    df = df.copy()
    _validate_xy(df)
    x_label, y_label = _xy_labels(df)
    x_mid = (float(df["x"].min()) + float(df["x"].max())) / 2
    y_mid = (float(df["y"].min()) + float(df["y"].max())) / 2

    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
    ax.scatter(df["x"], df["y"], s=90)
    for _, r in df.iterrows():
        mark = "*" if str(r.get("manual_confirmation", "")).lower() in {"true", "1", "yes"} else ""
        ax.annotate(f"{r['competitor']}{mark}", (r["x"], r["y"]), xytext=(6, 6), textcoords="offset points")
    ax.axvline(x_mid, linestyle="--", linewidth=1)
    ax.axhline(y_mid, linestyle="--", linewidth=1)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title or f"竞品四象限：{x_label} × {y_label}")
    fig.tight_layout()
    path = out / "quadrant.png"
    fig.savefig(path, dpi=DEFAULT_DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def matrix(df: pd.DataFrame, out: Path, title: str | None = None):
    df = df.copy()
    _validate_xy(df)
    x_label, y_label = _xy_labels(df)
    if "bubble" in df.columns:
        bubble = pd.to_numeric(df["bubble"], errors="coerce").fillna(40).clip(lower=1)
        sizes = 40 + 4 * bubble
    else:
        sizes = np.full(len(df), 120.0)

    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
    ax.scatter(df["x"], df["y"], s=sizes, alpha=0.65)
    for _, r in df.iterrows():
        mark = "*" if str(r.get("manual_confirmation", "")).lower() in {"true", "1", "yes"} else ""
        ax.annotate(f"{r['competitor']}{mark}", (r["x"], r["y"]), xytext=(6, 6), textcoords="offset points")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title or f"竞品定位矩阵：{x_label} × {y_label}")
    fig.tight_layout()
    path = out / "matrix.png"
    fig.savefig(path, dpi=DEFAULT_DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def main():
    configure_fonts()
    p = argparse.ArgumentParser(description="根据可编辑原始数据重新生成竞品定位图")
    p.add_argument("--input", required=True, help="雷达图使用宽表 CSV；quadrant/matrix 使用 XY CSV")
    p.add_argument("--xy-input", help="当 --type all 且 --input 为雷达数据时，用此参数指定 XY CSV")
    p.add_argument("--type", choices=["radar", "quadrant", "matrix", "all"], required=True)
    p.add_argument("--output-dir", default="charts_out")
    p.add_argument("--title", help="可选：覆盖默认图表标题")
    args = p.parse_args()

    out = ensure_output_dir(args.output_dir)
    made = []

    if args.type == "radar":
        made.append(radar(load_csv(args.input), out, args.title))
    elif args.type == "quadrant":
        made.append(quadrant(load_csv(args.input), out, args.title))
    elif args.type == "matrix":
        made.append(matrix(load_csv(args.input), out, args.title))
    else:
        radar_df = load_csv(args.input)
        xy_df = load_csv(args.xy_input or args.input)
        made.append(radar(radar_df, out, args.title))
        made.append(quadrant(xy_df, out, args.title))
        made.append(matrix(xy_df, out, args.title))

    for path in made:
        print(path)


if __name__ == "__main__":
    main()
