# -*- coding: utf-8 -*-
"""Color palette, fonts, and ttk style bootstrap."""

from tkinter import ttk


# ---------------------------------------------------------------- palette --
class Theme:
    BG          = "#0d1017"   # window background
    BG_2        = "#121722"   # secondary background (bottom bar)
    CARD        = "#1a1f2e"   # card surface
    CARD_HI     = "#232a3d"   # card highlight
    BORDER      = "#2a3145"
    BORDER_HI   = "#3a4260"
    SHADOW      = "#080a10"

    ACCENT      = "#6c7bff"
    ACCENT_HI   = "#8b97ff"
    ACCENT_LO   = "#4d5cdb"
    GRADIENT_A  = "#6c7bff"
    GRADIENT_B  = "#a855f7"

    SUCCESS     = "#22c55e"
    DANGER      = "#ef4444"
    WARN        = "#f59e0b"

    TEXT        = "#e8eaf2"
    TEXT_DIM    = "#a0a8bd"
    TEXT_MUTED  = "#6b7385"


FONT_TITLE   = ("Segoe UI Semibold", 18)
FONT_SUB     = ("Segoe UI", 10)
FONT_HEADING = ("Segoe UI Semibold", 12)
FONT_UI      = ("Segoe UI", 10)
FONT_UI_BOLD = ("Segoe UI Semibold", 10)
FONT_BUTTON  = ("Segoe UI Semibold", 10)
FONT_MONO    = ("Consolas", 9)


# ----------------------------------------------------------- color maths --
def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(
        *[max(0, min(255, int(c))) for c in rgb]
    )


def shade(hex_color: str, factor: float) -> str:
    """factor > 1 → lighter, < 1 → darker."""
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex((r * factor, g * factor, b * factor))


def mix(hex_a: str, hex_b: str, t: float) -> str:
    ra, ga, ba = _hex_to_rgb(hex_a)
    rb, gb, bb = _hex_to_rgb(hex_b)
    return _rgb_to_hex((
        ra + (rb - ra) * t,
        ga + (gb - ga) * t,
        ba + (bb - ba) * t,
    ))


# ----------------------------------------------------------- ttk styling --
def install_ttk_styles(root):
    """Configure 'clam' theme with dark custom styles."""
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".",
        background=Theme.BG,
        foreground=Theme.TEXT,
        fieldbackground=Theme.CARD,
        bordercolor=Theme.BORDER,
        lightcolor=Theme.BORDER,
        darkcolor=Theme.BORDER,
        troughcolor=Theme.CARD,
        focuscolor=Theme.ACCENT,
        font=FONT_UI,
    )

    # ---- Entries --------------------------------------------------------
    style.configure("Dark.TEntry",
        fieldbackground=Theme.CARD_HI,
        background=Theme.CARD_HI,
        foreground=Theme.TEXT,
        bordercolor=Theme.BORDER,
        insertcolor=Theme.TEXT,
        lightcolor=Theme.CARD_HI,
        darkcolor=Theme.CARD_HI,
        padding=8,
    )
    style.map("Dark.TEntry",
        bordercolor=[("focus", Theme.ACCENT)],
        lightcolor=[("focus", Theme.ACCENT)],
        darkcolor=[("focus", Theme.ACCENT)],
    )

    # ---- Combobox -------------------------------------------------------
    style.configure("Dark.TCombobox",
        fieldbackground=Theme.CARD_HI,
        background=Theme.CARD_HI,
        foreground=Theme.TEXT,
        arrowcolor=Theme.TEXT_DIM,
        bordercolor=Theme.BORDER,
        lightcolor=Theme.CARD_HI,
        darkcolor=Theme.CARD_HI,
        padding=6,
    )
    style.map("Dark.TCombobox",
        fieldbackground=[("readonly", Theme.CARD_HI)],
        bordercolor=[("focus", Theme.ACCENT)],
        arrowcolor=[("active", Theme.ACCENT)],
    )
    root.option_add("*TCombobox*Listbox.background", Theme.CARD_HI)
    root.option_add("*TCombobox*Listbox.foreground", Theme.TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", Theme.ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.font", FONT_UI)

    # ---- Spinbox --------------------------------------------------------
    style.configure("Dark.TSpinbox",
        fieldbackground=Theme.CARD_HI,
        background=Theme.CARD_HI,
        foreground=Theme.TEXT,
        arrowcolor=Theme.TEXT_DIM,
        bordercolor=Theme.BORDER,
        lightcolor=Theme.CARD_HI,
        darkcolor=Theme.CARD_HI,
        padding=6,
    )
    style.map("Dark.TSpinbox",
        bordercolor=[("focus", Theme.ACCENT)],
    )

    # ---- Checkbutton ----------------------------------------------------
    style.configure("Dark.TCheckbutton",
        background=Theme.CARD,
        foreground=Theme.TEXT_DIM,
        focuscolor=Theme.CARD,
        font=FONT_UI,
    )
    style.map("Dark.TCheckbutton",
        background=[("active", Theme.CARD)],
        foreground=[("active", Theme.TEXT)],
        indicatorcolor=[
            ("selected", Theme.ACCENT),
            ("!selected", Theme.CARD_HI),
        ],
    )

    # ---- Progress bar ---------------------------------------------------
    style.configure("Neon.Horizontal.TProgressbar",
        troughcolor=Theme.CARD,
        background=Theme.ACCENT,
        bordercolor=Theme.CARD,
        lightcolor=Theme.ACCENT_HI,
        darkcolor=Theme.ACCENT_LO,
        thickness=10,
    )

    # ---- Scrollbars -----------------------------------------------------
    style.configure("Dark.Vertical.TScrollbar",
        background=Theme.CARD_HI,
        troughcolor=Theme.CARD,
        bordercolor=Theme.CARD,
        arrowcolor=Theme.TEXT_DIM,
        lightcolor=Theme.CARD_HI,
        darkcolor=Theme.CARD_HI,
    )
    style.map("Dark.Vertical.TScrollbar",
        background=[("active", Theme.ACCENT)],
    )

    return style