# -*- coding: utf-8 -*-
"""Custom hand-drawn 3D widgets: buttons, cards, gradients, badges, tooltips."""

import tkinter as tk

from .theme import (
    Theme, FONT_BUTTON, FONT_HEADING,
    shade, _hex_to_rgb,
)


# =========================================================================== #
#  3D BUTTON
# =========================================================================== #
class Button3D(tk.Canvas):
    """Canvas-drawn button with a 3D base + face, hover & press states."""

    def __init__(self, parent, text="", command=None,
                 width=180, height=42, radius=10,
                 bg=Theme.ACCENT, fg="#ffffff",
                 hover=None, press=None,
                 font=FONT_BUTTON, icon="",
                 parent_bg=Theme.CARD):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, bd=0, bg=parent_bg)

        self._cw, self._ch = width, height
        self._radius = radius
        self._bg = bg
        self._bg_hover = hover or shade(bg, 1.15)
        self._bg_press = press or shade(bg, 0.82)
        self._fg = fg
        self._font = font
        self._text = text
        self._icon = icon
        self._command = command
        self._state = "idle"
        self._enabled = True

        self.bind("<Enter>",           self._on_enter)
        self.bind("<Leave>",           self._on_leave)
        self.bind("<Button-1>",        self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

        self._render()

    def _round_rect(self, x1, y1, x2, y2, r, fill):
        r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
        pts = [
            x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1,
            x2, y1, x2, y1, x2, y1+r, x2, y1+r,
            x2, y2-r, x2, y2-r, x2, y2, x2, y2,
            x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2,
            x1, y2, x1, y2, x1, y2-r, x1, y2-r,
            x1, y1+r, x1, y1+r, x1, y1, x1, y1,
        ]
        return self.create_polygon(pts, smooth=True, fill=fill, outline="")

    def _render(self):
        self.delete("all")
        w, h, r = self._cw, self._ch, self._radius
        depth = 3

        if not self._enabled:
            face = shade(self._bg, 0.35)
            base = shade(self._bg, 0.22)
            txt  = shade(self._fg, 0.55)
            press = False
        elif self._state == "press":
            face = self._bg_press
            base = shade(self._bg_press, 0.5)
            txt  = self._fg
            press = True
        elif self._state == "hover":
            face = self._bg_hover
            base = shade(self._bg_hover, 0.5)
            txt  = self._fg
            press = False
        else:
            face = self._bg
            base = shade(self._bg, 0.5)
            txt  = self._fg
            press = False

        if press:
            face_y = depth
            face_h = h - depth
        else:
            face_y = 0
            face_h = h - depth

        self._round_rect(0, depth, w, h, r, base)
        self._round_rect(0, face_y, w, face_y + face_h, r, face)
        self.create_line(r, face_y + 1, w - r, face_y + 1,
                         fill=shade(face, 1.4))

        display = f"{self._icon}   {self._text}" if self._icon else self._text
        self.create_text(w / 2, face_y + face_h / 2, text=display,
                         fill=txt, font=self._font)

    def _on_enter(self, _):
        if not self._enabled:
            return
        self._state = "hover"
        self._render()

    def _on_leave(self, _):
        if not self._enabled:
            return
        self._state = "idle"
        self._render()

    def _on_press(self, _):
        if not self._enabled:
            return
        self._state = "press"
        self._render()

    def _on_release(self, event):
        if not self._enabled:
            return
        self._state = "hover"
        self._render()
        if 0 <= event.x <= self._cw and 0 <= event.y <= self._ch:
            if self._command:
                self._command()

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self._state = "idle"
        self._render()

    def set_text(self, text: str):
        self._text = text
        self._render()


# =========================================================================== #
#  3D CARD
# =========================================================================== #
class Card(tk.Frame):
    """Container with a 1-px border + drop-shadow underneath."""

    def __init__(self, parent, title="", subtitle="", accent=None):
        shadow = tk.Frame(parent, bg=Theme.SHADOW)

        super().__init__(
            shadow, bg=Theme.CARD, bd=0,
            highlightthickness=1,
            highlightbackground=Theme.BORDER,
            highlightcolor=Theme.BORDER,
        )

        self._shadow = shadow
        super().pack(fill="both", expand=True, padx=(2, 0), pady=(2, 0))

        if title:
            head = tk.Frame(self, bg=Theme.CARD)
            head.pack(fill="x", padx=14, pady=(12, 4))

            if accent:
                bar = tk.Frame(head, bg=accent, width=3, height=18)
                bar.pack(side="left", padx=(0, 10))
                bar.pack_propagate(False)

            tk.Label(head, text=title, bg=Theme.CARD, fg=Theme.TEXT,
                     font=FONT_HEADING, anchor="w").pack(side="left")

            if subtitle:
                tk.Label(head, text=subtitle, bg=Theme.CARD,
                         fg=Theme.TEXT_MUTED, font=("Segoe UI", 9),
                         anchor="w").pack(side="left", padx=(10, 0))

        self.body = tk.Frame(self, bg=Theme.CARD)
        self.body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    def pack(self, *a, **kw):
        self._shadow.pack(*a, **kw)

    def grid(self, *a, **kw):
        self._shadow.grid(*a, **kw)


# =========================================================================== #
#  GRADIENT HEADER
# =========================================================================== #
class GradientHeader(tk.Canvas):
    def __init__(self, parent, height=88,
                 color_a=Theme.GRADIENT_A, color_b=Theme.GRADIENT_B,
                 title="", subtitle=""):
        super().__init__(parent, height=height, highlightthickness=0, bd=0,
                         bg=Theme.BG)
        self._gh = height
        self._ca = color_a
        self._cb = color_b
        self._title = title
        self._subtitle = subtitle
        self.bind("<Configure>", self._redraw)
        self.after(20, self._redraw)

    def _redraw(self, _=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2:
            return

        steps = max(80, w // 3)
        ra, ga, ba = _hex_to_rgb(self._ca)
        rb, gb, bb = _hex_to_rgb(self._cb)

        for i in range(steps):
            t = i / (steps - 1)
            r = int(ra + (rb - ra) * t)
            g = int(ga + (gb - ga) * t)
            b = int(ba + (bb - ba) * t)
            x1 = int(w * i / steps)
            x2 = int(w * (i + 1) / steps) + 1
            self.create_rectangle(x1, 0, x2, h,
                                  fill=f"#{r:02x}{g:02x}{b:02x}",
                                  outline="")

        self.create_rectangle(0, h - 1, w, h,
                              fill=shade(self._cb, 0.4), outline="")

        self.create_text(34, h / 2 - 13, anchor="w",
                         text=self._title,
                         fill="#ffffff",
                         font=("Segoe UI Semibold", 20))
        self.create_text(34, h / 2 + 15, anchor="w",
                         text=self._subtitle,
                         fill="#e8eaf2",
                         font=("Segoe UI", 10))


# =========================================================================== #
#  BADGE
# =========================================================================== #
class Badge(tk.Canvas):
    def __init__(self, parent, text="", color=Theme.ACCENT,
                 bg=Theme.CARD, height=22):
        self._font = ("Segoe UI Semibold", 9)
        self._color = color
        self._text = text
        self._badge_h = height
        self._parent = parent

        w = self._measure(text)
        super().__init__(parent, width=w, height=height,
                         highlightthickness=0, bd=0, bg=bg)
        self._redraw()

    def _measure(self, text):
        tmp = tk.Label(self._parent, text=text, font=self._font)
        tmp.update_idletasks()
        w = tmp.winfo_reqwidth() + 22
        tmp.destroy()
        return w

    def _round_rect(self, x1, y1, x2, y2, r, fill):
        r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
        pts = [x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1,
               x2, y1, x2, y1, x2, y1+r, x2, y1+r,
               x2, y2-r, x2, y2-r, x2, y2, x2, y2,
               x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2,
               x1, y2, x1, y2, x1, y2-r, x1, y2-r,
               x1, y1+r, x1, y1+r, x1, y1, x1, y1]
        return self.create_polygon(pts, smooth=True, fill=fill, outline="")

    def _redraw(self):
        self.delete("all")
        w = self._measure(self._text)
        h = self._badge_h
        self.configure(width=w, height=h)

        self._round_rect(0, 0, w, h, h // 2,
                         fill=shade(self._color, 0.35))
        self.create_text(w / 2, h / 2, text=self._text,
                         fill=self._color, font=self._font)

    def set_text(self, text):
        self._text = text
        self._redraw()


# =========================================================================== #
#  TOOLTIP  — hover to show a small help bubble
# =========================================================================== #
class Tooltip:
    """
    Attach to any widget:  Tooltip(my_widget, "Help text here")
    Shows a small popup after a short hover delay.
    """

    def __init__(self, widget, text, delay=450, wraplength=320):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.wraplength = wraplength
        self._after_id = None
        self._tip = None

        widget.bind("<Enter>",       self._on_enter, add="+")
        widget.bind("<Leave>",       self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _=None):
        self._after_id = self.widget.after(self.delay, self._show)

    def _on_leave(self, _=None):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self._tip:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None

    def _show(self):
        if self._tip or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        except Exception:
            return

        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        self._tip.attributes("-topmost", True)

        frame = tk.Frame(self._tip, bg=Theme.CARD_HI,
                         highlightthickness=1,
                         highlightbackground=Theme.BORDER_HI)
        frame.pack()

        tk.Label(frame, text=self.text, bg=Theme.CARD_HI, fg=Theme.TEXT,
                 font=("Segoe UI", 9), padx=12, pady=8,
                 justify="left", wraplength=self.wraplength
                 ).pack()


# =========================================================================== #
#  SEPARATOR
# =========================================================================== #
class HLine(tk.Frame):
    def __init__(self, parent, color=Theme.BORDER):
        super().__init__(parent, bg=color, height=1)