# theme.py
"""界面调色板与 ttk 样式，集中在这里以便 ui.py 只负责行为。"""
from tkinter import ttk

BG = "#f4f6f8"
CARD = "#ffffff"
BORDER = "#d7dde4"
TEXT = "#1f2937"
MUTED = "#6b7280"
ACCENT = "#2563eb"
SELECTED = "#e5effb"
GOOD = "#15803d"
BAD = "#b91c1c"
ROW_ALT = "#f8fafc"
GRID = "#e5e7eb"

FONT = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_METRIC = ("Segoe UI", 13, "bold")


def apply_style(root) -> ttk.Style:
    style = ttk.Style(root)
    # clam 是 Windows 上唯一能可靠自定义背景的主题
    style.theme_use("clam")
    style.configure(".", font=FONT, background=BG, foreground=TEXT)

    style.configure("Root.TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD, relief="flat", borderwidth=1)
    style.configure("Title.TLabel", font=FONT_TITLE, foreground=TEXT, background=BG)
    style.configure("Section.TLabel", font=FONT_BOLD, foreground=TEXT, background=CARD)
    style.configure("Subtle.TLabel", font=FONT_SMALL, foreground=MUTED, background=CARD)
    style.configure("Status.TLabel", font=FONT_SMALL, foreground=MUTED, background=BG)
    style.configure("Success.TLabel", font=FONT_SMALL, foreground=GOOD, background=BG)
    style.configure("Error.TLabel", font=FONT_SMALL, foreground=BAD, background=BG)
    style.configure("Metric.TLabel", font=FONT_METRIC, foreground=TEXT, background=CARD)
    style.configure("MetricDetail.TLabel", font=FONT_SMALL, foreground=MUTED, background=CARD)

    style.configure(
        "Choice.TButton",
        background=CARD,
        foreground=TEXT,
        bordercolor=BORDER,
        relief="flat",
        padding=(10, 6),
    )
    style.configure(
        "Selected.TButton",
        background=SELECTED,
        foreground=ACCENT,
        bordercolor=ACCENT,
        relief="flat",
        padding=(10, 6),
    )
    style.configure(
        "Primary.TButton",
        background=ACCENT,
        foreground="#ffffff",
        bordercolor=ACCENT,
        relief="flat",
        padding=(12, 6),
    )
    style.configure(
        "Ghost.TButton",
        background="#eef2f6",
        foreground=TEXT,
        bordercolor=BORDER,
        relief="flat",
        padding=(10, 6),
    )
    style.configure(
        "Danger.TButton",
        background="#fee2e2",
        foreground=BAD,
        bordercolor="#fca5a5",
        relief="flat",
        padding=(10, 6),
    )

    style.configure("TEntry", background=CARD, foreground=TEXT, bordercolor=BORDER,
                    insertcolor=TEXT, relief="flat", padding=(6, 4))
    style.configure("TCombobox", background=CARD, foreground=TEXT, bordercolor=BORDER,
                    relief="flat", padding=(6, 4))

    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", font=FONT, background="#e8edf2",
                    foreground=MUTED, padding=(12, 6))
    style.map("TNotebook.Tab",
              background=[("selected", CARD)],
              foreground=[("selected", TEXT)])

    style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
                    bordercolor=BORDER, rowheight=24)
    style.configure("Treeview.Heading", font=FONT_BOLD, foreground=TEXT,
                    background="#eef2f6", relief="flat")

    return style
