# charts.py
from datetime import datetime

import matplotlib
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator

import theme

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


def _style_ax(ax, title: str) -> None:
    ax.set_facecolor(theme.CARD)
    ax.grid(True, color=theme.GRID, linewidth=0.8)
    ax.set_title(title, color=theme.TEXT, fontweight="bold")
    ax.tick_params(colors=theme.MUTED)
    # get_xlabel() 返回字符串，颜色要写在 Text 对象上
    ax.xaxis.label.set_color(theme.MUTED)
    ax.yaxis.label.set_color(theme.MUTED)
    for spine in ax.spines.values():
        spine.set_color(theme.BORDER)


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


def _placeholder(ax) -> None:
    ax.text(0.5, 0.5, "暂无数据", ha="center", va="center", color=theme.MUTED)
    ax.axis("off")


def draw_coin_rate(ax, daily_counts: list[dict]) -> None:
    if not daily_counts:
        _placeholder(ax)
        return
    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_counts]
    rates = [d["coin_wins"] / d["total"] * 100 for d in daily_counts]
    ax.plot(dates, rates, marker="o", color=theme.ACCENT)
    ax.axhline(50, linestyle="--", color=theme.MUTED)
    ax.set_ylabel("硬币胜率 (%)")
    _configure_date_axis(ax, dates)
    _style_ax(ax, "每日硬币胜率趋势")


def draw_daily_counts(ax, daily_counts: list[dict]) -> None:
    if not daily_counts:
        _placeholder(ax)
        return
    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_counts]
    totals = [d["total"] for d in daily_counts]
    ax.bar(dates, totals, color=theme.ACCENT)
    ax.set_ylabel("局数")
    # 局数是整数，默认刻度会为 total=1 选出 0.25、0.5 这类无意义的刻度
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    _configure_date_axis(ax, dates)
    _style_ax(ax, "每日局数")


def draw_per_duel(ax, records: list[dict]) -> None:
    if not records:
        _placeholder(ax)
        return
    index = list(range(1, len(records) + 1))
    scores = [1 if r["coin_win"] else -1 for r in records]
    net = []
    running = 0
    for score in scores:
        running += score
        net.append(running)
    wins = [r["coin_win"] for r in records]
    cumulative_rate = [sum(wins[:i + 1]) / (i + 1) * 100 for i in range(len(wins))]

    # 主轴：每局赢 +1 / 输 -1 累加成的输赢差；次轴：累计胜率，两者单位不同
    ax.plot(index, net, color=theme.ACCENT, label="硬币输赢走势（赢 +1 / 输 -1）")
    ax.axhline(0, linestyle="--", color=theme.MUTED)
    ax.set_ylabel("赢 − 输")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    # 局数是整数，默认刻度会出现 0.5、1.5 这类无意义的半局刻度
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=MAX_DATE_TICKS))
    ax.set_xlabel("第 N 局")

    rate_ax = ax.twinx()
    rate_ax.plot(index, cumulative_rate, color=theme.GOOD, label="累计硬币胜率")
    rate_ax.set_ylabel("累计胜率 (%)")
    rate_ax.grid(False)
    rate_ax.tick_params(colors=theme.MUTED)
    rate_ax.yaxis.label.set_color(theme.MUTED)
    for spine in rate_ax.spines.values():
        spine.set_color(theme.BORDER)

    handles, labels = ax.get_legend_handles_labels()
    extra_handles, extra_labels = rate_ax.get_legend_handles_labels()
    # 右下角在这类图上通常是空白，放这里不会压住曲线
    ax.legend(handles + extra_handles, labels + extra_labels, loc="lower right")
    _style_ax(ax, "逐局硬币趋势")
