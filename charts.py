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

MAX_DATE_TICKS = 12


def _configure_date_axis(ax, dates: list[datetime]) -> None:
    # AutoDateLocator 会为短区间选到小时刻度、长区间选到月度刻度，
    # 而 %m-%d 格式化后这些刻度会显示成重复标签；因此刻度取自真实日期。
    unique = sorted(set(dates))
    if len(unique) > MAX_DATE_TICKS:
        step = -(-len(unique) // MAX_DATE_TICKS)  # ceil
        unique = unique[::step]
    ax.set_xticks(unique)
    span = (max(dates) - min(dates)).days
    fmt = "%Y-%m-%d" if span > 365 else "%m-%d"
    ax.xaxis.set_major_formatter(mdates.DateFormatter(fmt))
    ax.tick_params(axis="x", rotation=45)


def _placeholder(fig: Figure) -> Figure:
    ax = fig.subplots()
    ax.text(0.5, 0.5, "暂无数据", ha="center", va="center")
    ax.axis("off")
    return fig


def build_figures(daily_counts: list[dict], records: list[dict]) -> list[Figure]:
    if not daily_counts:
        rate_fig = _placeholder(Figure(figsize=(8, 4)))
    else:
        rate_fig = Figure(figsize=(8, 4))
        ax = rate_fig.subplots()
        dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_counts]
        rates = [d["coin_wins"] / d["total"] * 100 for d in daily_counts]
        ax.plot(dates, rates, marker="o")
        ax.axhline(50, linestyle="--", color="gray")
        ax.set_ylabel("硬币胜率 (%)")
        ax.set_title("每日硬币胜率趋势")
        _configure_date_axis(ax, dates)

    if not daily_counts:
        counts_fig = _placeholder(Figure(figsize=(8, 4)))
    else:
        counts_fig = Figure(figsize=(8, 4))
        ax = counts_fig.subplots()
        dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_counts]
        totals = [d["total"] for d in daily_counts]
        ax.bar(dates, totals)
        ax.set_ylabel("对数")
        ax.set_title("每日对数")
        _configure_date_axis(ax, dates)

    if not records:
        duel_fig = _placeholder(Figure(figsize=(8, 4)))
    else:
        duel_fig = Figure(figsize=(8, 4))
        ax = duel_fig.subplots()
        index = list(range(1, len(records) + 1))
        results = [r["coin_win"] * 100 for r in records]
        cumulative = [sum(results[:i + 1]) / (i + 1) for i in range(len(results))]
        ax.plot(index, results, marker="o", linestyle="", label="每局硬币")
        ax.plot(index, cumulative, marker=".", label="累计硬币胜率")
        ax.axhline(50, linestyle="--", color="gray")
        ax.set_ylim(0, 100)
        ax.set_xlabel("第 N 局")
        ax.set_ylabel("百分比 (%)")
        ax.set_title("逐局硬币趋势")
        ax.legend()

    return [rate_fig, counts_fig, duel_fig]
