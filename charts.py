# charts.py
from datetime import datetime

import matplotlib
import matplotlib.dates as mdates
from matplotlib.figure import Figure

# 图表文案为中文，默认字体 DejaVu Sans 不含汉字字形；按平台回退到可用字体
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "PingFang SC",
    "Noto Sans CJK SC",
    "SimHei",
    "DejaVu Sans",
]


def build_figures(daily_counts: list[dict]) -> list[Figure]:
    rate_fig = Figure(figsize=(8, 4))
    counts_fig = Figure(figsize=(8, 4))
    rate_ax = rate_fig.subplots()
    counts_ax = counts_fig.subplots()

    if not daily_counts:
        for ax in (rate_ax, counts_ax):
            ax.text(0.5, 0.5, "暂无数据", ha="center", va="center")
            ax.axis("off")
        return [rate_fig, counts_fig]

    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_counts]
    rates = [d["coin_wins"] / d["total"] * 100 for d in daily_counts]
    totals = [d["total"] for d in daily_counts]

    rate_ax.plot(dates, rates, marker="o")
    rate_ax.axhline(50, linestyle="--", color="gray")
    rate_ax.set_ylabel("硬币胜率 (%)")
    rate_ax.set_title("每日硬币胜率趋势")

    counts_ax.bar(dates, totals)
    counts_ax.set_ylabel("对数")
    counts_ax.set_title("每日对数")

    for ax in (rate_ax, counts_ax):
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.tick_params(axis="x", rotation=45)

    return [rate_fig, counts_fig]
