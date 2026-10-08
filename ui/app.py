# -*- coding: utf-8 -*-
"""Friendly main window — guided 4-step workflow."""

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from .theme import (
    Theme, FONT_UI, FONT_UI_BOLD, FONT_MONO,
    install_ttk_styles, shade,
)
from .widgets import Button3D, Card, GradientHeader, Tooltip
from core.presets import (
    PRESETS, FIT_PAD, FIT_CROP, FIT_BLUR,
    POSITIONS, ENC_PRESETS, VIDEO_EXTS,
)
from core.engine import RenderWorker, locate_binary, scan_folder


APP_TITLE = "Video Watermarker"

# ---- Friendly presentation of the format presets ---------------------------
FRIENDLY_FORMATS = [
    {
        "key":   "9:16  Vertical Shorts   — 1080 x 1920",
        "tag":   "9:16",
        "title": "Vertical",
        "sub":   "TikTok · Reels · Shorts",
        "size":  "1080 × 1920",
    },
    {
        "key":   "1:1   Square Feed       — 1080 x 1080",
        "tag":   "1:1",
        "title": "Square",
        "sub":   "Instagram · Facebook feed",
        "size":  "1080 × 1080",
    },
    {
        "key":   "16:9  Widescreen        — 1920 x 1080",
        "tag":   "16:9",
        "title": "Widescreen",
        "sub":   "YouTube · Websites",
        "size":  "1920 × 1080",
    },
]

FIT_LABELS = {
    FIT_PAD:  "Show the whole video (adds bars if needed)",
    FIT_CROP: "Fill the screen (zooms in, trims edges)",
    FIT_BLUR: "Fill the screen (blurred background)",
}
FIT_BY_LABEL = {v: k for k, v in FIT_LABELS.items()}


class WatermarkerApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Video Watermarker — Add your logo & resize videos")
        self.geometry("1180x820")
        self.minsize(1020, 720)
        self.configure(bg=Theme.BG)

        install_ttk_styles(self)

        # -- binaries ------------------------------------------------------
        self.ffmpeg  = locate_binary("ffmpeg")
        self.ffprobe = locate_binary("ffprobe")

        # -- runtime state -------------------------------------------------
        self.msg_q = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker = None
        self.source_files = []
        self._format_pills = {}
        self._adv_open = False
        self._adv_built = False

        # -- tk vars -------------------------------------------------------
        self.var_logo     = tk.StringVar()
        self.var_outdir   = tk.StringVar()
        self.var_preset   = tk.StringVar(value=FRIENDLY_FORMATS[0]["key"])
        self.var_fit      = tk.StringVar(value=FIT_PAD)
        self.var_pos      = tk.StringVar(value="Bottom-Right")
        self.var_scale    = tk.DoubleVar(value=15.0)
        self.var_opacity  = tk.DoubleVar(value=0.85)
        self.var_crf      = tk.IntVar(value=23)
        self.var_enc      = tk.StringVar(value="veryfast")
        self.var_suffix   = tk.StringVar(value="_formatted")
        self.var_recursive = tk.BooleanVar(value=True)

        self._build_ui()
        self._poll_queue()
        self._refresh_format_highlight()

        # -- FFmpeg startup check ------------------------------------------
        if not self.ffmpeg:
            self._set_action_warning(
                "FFmpeg was not found — the app can't process videos.",
                "Place ffmpeg.exe + ffprobe.exe in the bin folder next to this app.",
            )

    # ================================================================= UI ==
    def _build_ui(self):
        # ---- HEADER -------------------------------------------------------
        GradientHeader(
            self, height=92,
            title="Video Watermarker",
            subtitle="Add your logo · Resize for TikTok, Reels & YouTube",
        ).pack(fill="x")

        # ---- BOTTOM ACTION BAR -------------------------------------------
        bottom = tk.Frame(self, bg=Theme.BG_2, height=118)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)
        tk.Frame(bottom, bg=Theme.BORDER, height=1).pack(fill="x", side="top")
        self._build_action_bar(bottom)

        # ---- MAIN BODY ----------------------------------------------------
        body = tk.Frame(self, bg=Theme.BG)
        body.pack(fill="both", expand=True, padx=22, pady=16)
        body.columnconfigure(0, weight=1, uniform="col")
        body.columnconfigure(1, weight=1, uniform="col")
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=Theme.BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        right = tk.Frame(body, bg=Theme.BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._build_step1_videos(left)
        self._build_step2_logo(left)
        self._build_step3_format(right)
        self._build_step4_output(right)

        # Advanced toggle + panel spans both columns
        adv_holder = tk.Frame(body, bg=Theme.BG)
        adv_holder.grid(row=1, column=0, columnspan=2,
                        sticky="ew", pady=(12, 0))
        self._build_advanced_section(adv_holder)

    # --------------------------------------------------------- step card --
    def _make_step_card(self, parent, number, title, subtitle, color):
        """Return (card, body) — a card with a numbered badge and title."""
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        body = card.body

        head = tk.Frame(body, bg=Theme.CARD)
        head.pack(fill="x", pady=(0, 10))

        # --- Number badge (canvas circle with number) -------------------
        num = tk.Canvas(head, width=34, height=34,
                        highlightthickness=0, bd=0, bg=Theme.CARD)
        num.pack(side="left", padx=(0, 12))
        num.create_oval(2, 2, 32, 32,
                        fill=shade(color, 0.22),
                        outline=color, width=1.5)
        num.create_text(17, 18, text=str(number),
                        fill=color,
                        font=("Segoe UI Semibold", 13))

        # --- Text block --------------------------------------------------
        txt = tk.Frame(head, bg=Theme.CARD)
        txt.pack(side="left", fill="x", expand=True)
        tk.Label(txt, text=title, bg=Theme.CARD, fg=Theme.TEXT,
                 font=("Segoe UI Semibold", 12), anchor="w").pack(fill="x")
        tk.Label(txt, text=subtitle, bg=Theme.CARD, fg=Theme.TEXT_MUTED,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x")

        return card, body

    # ---------------------------------------------------- STEP 1: videos --
    def _build_step1_videos(self, parent):
        card, body = self._make_step_card(
            parent, 1,
            "Pick your videos",
            "Add the clips you want to watermark & resize",
            Theme.ACCENT,
        )

        row = tk.Frame(body, bg=Theme.CARD)
        row.pack(fill="x")

        btn_folder = Button3D(
            row, text="Choose a Folder", command=self._pick_folder,
            width=190, height=42,
            bg=Theme.ACCENT, fg="#ffffff",
            parent_bg=Theme.CARD,
            font=("Segoe UI Semibold", 11),
        )
        btn_folder.pack(side="left")
        Tooltip(btn_folder,
                "Pick a folder that contains videos. Every video inside "
                "will be added to the queue (including subfolders).")

        btn_files = Button3D(
            row, text="Choose Files", command=self._add_files,
            width=150, height=42,
            bg=Theme.CARD_HI, fg=Theme.TEXT,
            parent_bg=Theme.CARD,
            font=("Segoe UI Semibold", 10),
        )
        btn_files.pack(side="left", padx=(10, 0))
        Tooltip(btn_files,
                "Pick individual video files. Hold Ctrl or Shift to "
                "select more than one at a time.")

        btn_clear = Button3D(
            row, text="Clear", command=self._clear_queue,
            width=90, height=42,
            bg=Theme.CARD_HI, fg=Theme.TEXT_DIM,
            parent_bg=Theme.CARD,
            font=("Segoe UI Semibold", 10),
        )
        btn_clear.pack(side="left", padx=(10, 0))
        Tooltip(btn_clear, "Remove every video from the queue.")

        self.lbl_queue = tk.Label(
            body, text="No videos added yet",
            bg=Theme.CARD, fg=Theme.TEXT_MUTED,
            font=("Segoe UI", 10), anchor="w", justify="left",
            wraplength=520,
        )
        self.lbl_queue.pack(fill="x", pady=(12, 0))

    # ------------------------------------------------------ STEP 2: logo --
    def _build_step2_logo(self, parent):
        card, body = self._make_step_card(
            parent, 2,
            "Add your logo  (optional)",
            "A PNG image that will appear on every video",
            Theme.GRADIENT_B,
        )

        row = tk.Frame(body, bg=Theme.CARD)
        row.pack(fill="x")

        btn_logo = Button3D(
            row, text="Choose Logo Image", command=self._pick_logo,
            width=200, height=42,
            bg=Theme.GRADIENT_B, fg="#ffffff",
            parent_bg=Theme.CARD,
            font=("Segoe UI Semibold", 11),
        )
        btn_logo.pack(side="left")
        Tooltip(btn_logo,
                "Pick a PNG file — like your brand logo or channel name. "
                "It will be placed on the bottom-right corner of every video.\n\n"
                "Skip this step if you only want to resize videos.")

        self.lbl_logo = tk.Label(
            body, text="No logo selected — videos will only be resized",
            bg=Theme.CARD, fg=Theme.TEXT_MUTED,
            font=("Segoe UI", 10), anchor="w", justify="left",
            wraplength=520,
        )
        self.lbl_logo.pack(fill="x", pady=(12, 0))

    # ---------------------------------------------------- STEP 3: format --
    def _build_step3_format(self, parent):
        card, body = self._make_step_card(
            parent, 3,
            "Choose the output format",
            "Pick where the videos will be posted",
            Theme.SUCCESS,
        )

        pills = tk.Frame(body, bg=Theme.CARD)
        pills.pack(fill="x")

        for meta in FRIENDLY_FORMATS:
            pill = self._make_format_pill(pills, meta)
            pill.pack(side="left", padx=(0, 8))
            self._format_pills[meta["key"]] = pill

        # ---- Fit mode (what to do if video shape doesn't match) --------
        fit_row = tk.Frame(body, bg=Theme.CARD)
        fit_row.pack(fill="x", pady=(14, 0))

        tk.Label(fit_row, text="If the video doesn't match:",
                 bg=Theme.CARD, fg=Theme.TEXT_DIM,
                 font=("Segoe UI", 9), anchor="w"
                 ).pack(anchor="w")

        self.cb_fit = ttk.Combobox(
            fit_row, values=list(FIT_LABELS.values()),
            state="readonly", style="Dark.TCombobox",
        )
        self.cb_fit.set(FIT_LABELS[FIT_PAD])
        self.cb_fit.pack(fill="x", pady=(4, 0))
        self.cb_fit.bind("<<ComboboxSelected>>", self._on_fit_selected)
        Tooltip(self.cb_fit,
                "• Show the whole video — nothing is cut off, but black bars "
                "may appear around it.\n"
                "• Fill the screen — the video is scaled up and edges get "
                "trimmed.\n"
                "• Blurred background — the video is centered over a "
                "blurred, zoomed copy of itself.")

    def _make_format_pill(self, parent, meta):
        """Clickable card for one format preset."""
        pill = tk.Frame(parent, bg=Theme.CARD,
                        highlightthickness=2,
                        highlightbackground=Theme.BORDER,
                        highlightcolor=Theme.BORDER,
                        cursor="hand2")

        inner = tk.Frame(pill, bg=Theme.CARD, padx=14, pady=11)
        inner.pack(fill="both", expand=True)

        tag = tk.Label(inner, text=meta["tag"], bg=Theme.CARD,
                       fg=Theme.TEXT_DIM,
                       font=("Segoe UI Semibold", 15), anchor="w")
        tag.pack(anchor="w")

        title = tk.Label(inner, text=meta["title"], bg=Theme.CARD,
                         fg=Theme.TEXT,
                         font=("Segoe UI Semibold", 11), anchor="w")
        title.pack(anchor="w", pady=(2, 0))

        sub = tk.Label(inner, text=meta["sub"], bg=Theme.CARD,
                       fg=Theme.TEXT_MUTED,
                       font=("Segoe UI", 8), anchor="w")
        sub.pack(anchor="w")

        size = tk.Label(inner, text=meta["size"], bg=Theme.CARD,
                        fg=Theme.TEXT_DIM,
                        font=("Consolas", 8), anchor="w")
        size.pack(anchor="w", pady=(4, 0))

        children = (pill, inner, tag, title, sub, size)

        def select(_=None):
            self.var_preset.set(meta["key"])
            self._refresh_format_highlight()

        for w in children:
            w.bind("<Button-1>", select)

        pill._all_children = children
        return pill

    def _refresh_format_highlight(self):
        current = self.var_preset.get()
        for key, pill in self._format_pills.items():
            selected = (key == current)
            border = Theme.ACCENT if selected else Theme.BORDER
            bg = shade(Theme.ACCENT, 0.20) if selected else Theme.CARD
            pill.configure(highlightbackground=border,
                           highlightcolor=border)
            for w in pill._all_children:
                try:
                    w.configure(bg=bg)
                except Exception:
                    pass

    def _on_fit_selected(self, _):
        label = self.cb_fit.get()
        if label in FIT_BY_LABEL:
            self.var_fit.set(FIT_BY_LABEL[label])

    # ---------------------------------------------------- STEP 4: output --
    def _build_step4_output(self, parent):
        card, body = self._make_step_card(
            parent, 4,
            "Where should we save the finished videos?",
            "Skip this — files save next to the originals by default",
            Theme.WARN,
        )

        row = tk.Frame(body, bg=Theme.CARD)
        row.pack(fill="x")

        btn_out = Button3D(
            row, text="Choose Output Folder", command=self._pick_output,
            width=200, height=42,
            bg=Theme.WARN, fg="#1a1f2e",
            parent_bg=Theme.CARD,
            font=("Segoe UI Semibold", 11),
        )
        btn_out.pack(side="left")
        Tooltip(btn_out,
                "Where the finished videos will be saved.\n\n"
                "Leave this alone to save each new video next to its "
                "original — inside a folder called '_watermarked'.")

        self.lbl_output = tk.Label(
            body, text="Default:  next to each original video",
            bg=Theme.CARD, fg=Theme.TEXT_MUTED,
            font=("Segoe UI", 10), anchor="w", justify="left",
            wraplength=520,
        )
        self.lbl_output.pack(fill="x", pady=(12, 0))

    # ------------------------------------------------------ ADVANCED -------
    def _build_advanced_section(self, parent):
        self._adv_toggle = tk.Label(
            parent, text="▸  Show advanced options",
            bg=Theme.BG, fg=Theme.ACCENT_HI,
            font=("Segoe UI Semibold", 10),
            cursor="hand2", anchor="w",
        )
        self._adv_toggle.pack(fill="x")
        self._adv_toggle.bind("<Button-1>", self._toggle_advanced)

        self._adv_frame = tk.Frame(parent, bg=Theme.BG)

    def _toggle_advanced(self, _=None):
        if self._adv_open:
            self._adv_frame.pack_forget()
            self._adv_toggle.configure(text="▸  Show advanced options")
            self._adv_open = False
            return

        if not self._adv_built:
            self._build_advanced_content()
            self._adv_built = True

        self._adv_frame.pack(fill="x", pady=(8, 0))
        self._adv_toggle.configure(text="▾  Hide advanced options")
        self._adv_open = True

    def _build_advanced_content(self):
        card = Card(self._adv_frame, title="Advanced options",
                    subtitle="Only touch these if you know what you want",
                    accent=Theme.TEXT_MUTED)
        card.pack(fill="x")
        body = card.body

        grid = tk.Frame(body, bg=Theme.CARD)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(2, weight=1)

        def field(label, row, col, factory):
            f = tk.Frame(grid, bg=Theme.CARD)
            f.grid(row=row, column=col, sticky="ew",
                   padx=(0, 10) if col < 2 else 0, pady=6)
            tk.Label(f, text=label, bg=Theme.CARD, fg=Theme.TEXT_DIM,
                     font=("Segoe UI", 9), anchor="w").pack(fill="x")
            w = factory(f)
            w.pack(fill="x", pady=(4, 0))
            return w

        field("Watermark corner", 0, 0,
              lambda p: ttk.Combobox(p, textvariable=self.var_pos,
                                     values=list(POSITIONS.keys()),
                                     state="readonly",
                                     style="Dark.TCombobox"))
        field("Watermark size (% of frame)", 0, 1,
              lambda p: ttk.Spinbox(p, from_=2, to=60, increment=1,
                                    textvariable=self.var_scale,
                                    style="Dark.TSpinbox"))
        field("Watermark opacity (0–1)", 0, 2,
              lambda p: ttk.Spinbox(p, from_=0.05, to=1.0, increment=0.05,
                                    textvariable=self.var_opacity,
                                    format="%.2f",
                                    style="Dark.TSpinbox"))
        field("Video quality (CRF — lower = better)", 1, 0,
              lambda p: ttk.Spinbox(p, from_=14, to=32, increment=1,
                                    textvariable=self.var_crf,
                                    style="Dark.TSpinbox"))
        field("Encoder speed", 1, 1,
              lambda p: ttk.Combobox(p, textvariable=self.var_enc,
                                     values=ENC_PRESETS,
                                     state="readonly",
                                     style="Dark.TCombobox"))
        field("Filename suffix", 1, 2,
              lambda p: ttk.Entry(p, textvariable=self.var_suffix,
                                  style="Dark.TEntry"))

        # Include-subfolder toggle
        ttk.Checkbutton(body, text="When picking a folder, also scan subfolders",
                        variable=self.var_recursive,
                        style="Dark.TCheckbutton"
                        ).pack(anchor="w", pady=(8, 6))

        # Tiny log box (useful if something goes wrong)
        tk.Label(body, text="Processing log",
                 bg=Theme.CARD, fg=Theme.TEXT_DIM,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x")
        self.console = tk.Text(
            body, height=6, wrap="word",
            bg=Theme.BG, fg=Theme.TEXT_DIM,
            insertbackground=Theme.TEXT,
            borderwidth=0, highlightthickness=1,
            highlightbackground=Theme.BORDER,
            font=FONT_MONO, state="disabled",
        )
        self.console.pack(fill="x", pady=(4, 0))
        self.console.tag_configure("info",    foreground=Theme.TEXT)
        self.console.tag_configure("muted",   foreground=Theme.TEXT_MUTED)
        self.console.tag_configure("success", foreground=Theme.SUCCESS)
        self.console.tag_configure("error",   foreground=Theme.DANGER)
        self.console.tag_configure("warn",    foreground=Theme.WARN)
        self.console.tag_configure("heading", foreground=Theme.ACCENT_HI,
                                   font=("Consolas", 9, "bold"))

    # ---------------------------------------------------- action bar ------
    def _build_action_bar(self, parent):
        wrap = tk.Frame(parent, bg=Theme.BG_2)
        wrap.pack(fill="both", expand=True, padx=22, pady=16)

        # PRIMARY button
        self.btn_start = Button3D(
            wrap, text="Start Processing", command=self._start_batch,
            width=260, height=62,
            bg=Theme.ACCENT, fg="#ffffff",
            parent_bg=Theme.BG_2,
            font=("Segoe UI Semibold", 13),
            icon="▶",
        )
        self.btn_start.pack(side="left")
        Tooltip(self.btn_start,
                "Process every queued video with your logo & chosen format.\n"
                "The originals are never modified — new files get created.")

        # MIDDLE — status + progress
        middle = tk.Frame(wrap, bg=Theme.BG_2)
        middle.pack(side="left", fill="both", expand=True, padx=(24, 12))

        self.lbl_action = tk.Label(
            middle, text="Ready when you are",
            bg=Theme.BG_2, fg=Theme.TEXT,
            font=("Segoe UI Semibold", 11), anchor="w",
        )
        self.lbl_action.pack(fill="x")

        self.lbl_sub = tk.Label(
            middle,
            text="Add a few videos above, then click Start Processing.",
            bg=Theme.BG_2, fg=Theme.TEXT_MUTED,
            font=("Segoe UI", 9), anchor="w", justify="left",
        )
        self.lbl_sub.pack(fill="x")

        row = tk.Frame(middle, bg=Theme.BG_2)
        row.pack(fill="x", pady=(8, 0))

        self.progress = ttk.Progressbar(
            row, mode="determinate", maximum=100,
            style="Neon.Horizontal.TProgressbar",
        )
        self.progress.pack(side="left", fill="x", expand=True)

        self.lbl_pct = tk.Label(
            row, text="", bg=Theme.BG_2, fg=Theme.ACCENT_HI,
            font=("Segoe UI Semibold", 10), width=7, anchor="e",
        )
        self.lbl_pct.pack(side="left", padx=(10, 0))

        # CANCEL button
        self.btn_cancel = Button3D(
            wrap, text="Stop", command=self._cancel_batch,
            width=110, height=48,
            bg=Theme.DANGER, fg="#ffffff",
            parent_bg=Theme.BG_2,
            font=("Segoe UI Semibold", 11),
        )
        self.btn_cancel.pack(side="right")
        self.btn_cancel.set_enabled(False)

    # ------------------------------------------------- status bar helpers --
    def _set_action_idle(self, title="Ready when you are",
                         sub="Add a few videos above, then click Start Processing."):
        self.lbl_action.config(text=title, fg=Theme.TEXT)
        self.lbl_sub.config(text=sub, fg=Theme.TEXT_MUTED)

    def _set_action_running(self, title, sub=""):
        self.lbl_action.config(text=title, fg=Theme.ACCENT_HI)
        self.lbl_sub.config(text=sub, fg=Theme.TEXT_MUTED)

    def _set_action_done(self, title, sub=""):
        self.lbl_action.config(text=title, fg=Theme.SUCCESS)
        self.lbl_sub.config(text=sub, fg=Theme.TEXT_MUTED)

    def _set_action_warning(self, title, sub=""):
        self.lbl_action.config(text=title, fg=Theme.WARN)
        self.lbl_sub.config(text=sub, fg=Theme.TEXT_MUTED)

    # ============================================================ actions ==
    def _pick_folder(self):
        folder = filedialog.askdirectory(
            title="Pick a folder that has videos inside")
        if not folder:
            return
        found = scan_folder(folder, self.var_recursive.get())
        if not found:
            messagebox.showinfo(
                "No videos found",
                "That folder doesn't contain any video files.\n\n"
                "Try a different folder, or use 'Choose Files' instead.",
            )
            return
        added = 0
        for f in found:
            if f not in self.source_files:
                self.source_files.append(f)
                added += 1
        self._refresh_queue()
        if added:
            self._set_action_idle(
                f"Ready to go — {len(self.source_files)} video(s) in the queue",
                "Click Start Processing when you're ready.",
            )

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Pick video files",
            filetypes=[
                ("Video files",
                 "*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.flv "
                 "*.wmv *.mpg *.mpeg *.ts *.3gp"),
                ("All files", "*.*"),
            ],
        )
        added = 0
        for p in paths:
            fp = Path(p)
            if fp.suffix.lower() in VIDEO_EXTS and fp not in self.source_files:
                self.source_files.append(fp)
                added += 1
        if added:
            self._refresh_queue()
            self._set_action_idle(
                f"Ready to go — {len(self.source_files)} video(s) in the queue",
                "Click Start Processing when you're ready.",
            )

    def _pick_logo(self):
        p = filedialog.askopenfilename(
            title="Pick your logo image (PNG)",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
        )
        if p:
            self.var_logo.set(p)
            self.lbl_logo.config(
                text=f"✓  {Path(p).name}",
                fg=Theme.SUCCESS,
            )

    def _pick_output(self):
        d = filedialog.askdirectory(
            title="Pick where to save the finished videos")
        if d:
            self.var_outdir.set(d)
            self.lbl_output.config(
                text=f"✓  {d}",
                fg=Theme.SUCCESS,
            )

    def _refresh_queue(self):
        n = len(self.source_files)
        if n == 0:
            self.lbl_queue.config(
                text="No videos added yet",
                fg=Theme.TEXT_MUTED,
            )
            return

        preview = ", ".join(p.name for p in self.source_files[:3])
        if n > 3:
            preview += f"  … and {n - 3} more"
        self.lbl_queue.config(
            text=f"✓  {n} video(s) ready:   {preview}",
            fg=Theme.SUCCESS,
        )

    def _clear_queue(self):
        self.source_files.clear()
        self._refresh_queue()
        self._set_action_idle()

    # ============================================================== engine ==
    def _start_batch(self):
        if self.worker and self.worker.is_alive():
            return

        if not self.ffmpeg:
            messagebox.showerror(
                "FFmpeg not found",
                "The app needs FFmpeg to process videos, but it wasn't found.\n\n"
                "Make sure ffmpeg.exe and ffprobe.exe are inside the "
                "'bin' folder next to this app.",
            )
            return

        if not self.source_files:
            messagebox.showinfo(
                "Add some videos first",
                "Click 'Choose a Folder' or 'Choose Files' in step 1 "
                "to add videos to the queue.",
            )
            return

        logo = self.var_logo.get().strip() or None
        if logo and not Path(logo).is_file():
            messagebox.showerror(
                "Logo file missing",
                f"Couldn't find this file:\n{logo}\n\n"
                "Pick the logo again.",
            )
            return

        # ---------- output folder -----------------------------------------
        outdir = self.var_outdir.get().strip()
        if not outdir:
            outdir = str(self.source_files[0].parent / "_watermarked")
        try:
            Path(outdir).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror(
                "Can't create the output folder",
                f"Windows says:\n{e}",
            )
            return

        # ---------- build config ------------------------------------------
        out_w, out_h = PRESETS[self.var_preset.get()]
        cfg = {
            "w": out_w, "h": out_h,
            "fit": self.var_fit.get(),
            "wm_scale": self.var_scale.get(),
            "wm_opacity": max(0.05, min(1.0, self.var_opacity.get())),
            "wm_pos": self.var_pos.get(),
            "crf": int(self.var_crf.get()),
            "enc": self.var_enc.get(),
            "suffix": self.var_suffix.get(),
        }

        # ---------- UI -> running state -----------------------------------
        self.cancel_event.clear()
        self.progress["value"] = 0
        self.lbl_pct.config(text="0 %")
        self.btn_start.set_enabled(False)
        self.btn_cancel.set_enabled(True)
        self._set_action_running(
            f"Processing {len(self.source_files)} video(s)…",
            "This can take a minute or two. The window stays responsive.",
        )

        # ---------- clear + start -----------------------------------------
        self._log("", "info")
        self._log("=" * 60, "heading")
        self._log(f"  Batch started  ·  {len(self.source_files)} clip(s)",
                  "heading")
        self._log(f"  Format   : {out_w} x {out_h}", "info")
        self._log(f"  Fit mode : {cfg['fit']}", "info")
        self._log(f"  Logo     : {logo or '(none)'}", "info")
        self._log(f"  Saving to: {outdir}", "info")
        self._log("=" * 60, "heading")

        self.worker = RenderWorker(
            files=list(self.source_files),
            outdir=outdir,
            logo=logo,
            cfg=cfg,
            ffmpeg=self.ffmpeg,
            ffprobe=self.ffprobe,
            msg_queue=self.msg_q,
            cancel_event=self.cancel_event,
        )
        self.worker.start()

    def _cancel_batch(self):
        if not (self.worker and self.worker.is_alive()):
            return
        self._log("Cancel requested — stopping the current render.", "warn")
        self._set_action_running("Stopping…", "Finishing up the current video.")
        self.worker.cancel()
        self.btn_cancel.set_enabled(False)

    # =============================================================== IPC ===
    def _poll_queue(self):
        try:
            while True:
                msg = self.msg_q.get_nowait()
                kind = msg[0]

                if kind == "log":
                    _, text, tag = msg
                    self._log(text, tag)

                elif kind == "status":
                    self.lbl_sub.config(text=msg[1])

                elif kind == "progress":
                    pct = msg[1]
                    self.progress["value"] = pct
                    self.lbl_pct.config(text=f"{pct:.0f} %")

                elif kind == "done":
                    _, ok, fail, elapsed, outdir = msg
                    self._on_done(ok, fail, elapsed, outdir)
        except queue.Empty:
            pass
        self.after(80, self._poll_queue)

    def _log(self, text, tag="info"):
        if not hasattr(self, "console"):
            return
        self.console.configure(state="normal")
        self.console.insert(tk.END, text + "\n", tag)
        self.console.see(tk.END)
        self.console.configure(state="disabled")

    def _on_done(self, ok, fail, elapsed, outdir):
        self.btn_start.set_enabled(True)
        self.btn_cancel.set_enabled(False)

        if fail == 0 and ok > 0:
            self._set_action_done(
                f"✓ Done!  {ok} video(s) processed successfully.",
                f"Saved to:  {outdir}",
            )
            self.lbl_pct.config(text="100 %")
        elif ok > 0:
            self._set_action_warning(
                f"Finished with issues — {ok} succeeded, {fail} failed.",
                f"Check the log (Show advanced options). Output: {outdir}",
            )
            self.lbl_pct.config(text="—")
        else:
            self._set_action_warning(
                "Nothing could be processed — see the log for details.",
                "Open 'Show advanced options' to read the error messages.",
            )
            self.lbl_pct.config(text="—")

        # Also drop details into the log
        self._log("", "info")
        self._log("-" * 60, "heading")
        self._log(
            f"  Batch complete  ·  {ok} succeeded  ·  {fail} failed  ·  "
            f"{elapsed:.1f}s",
            "success" if fail == 0 else "warn",
        )
        self._log(f"  Output: {outdir}", "info")
        self._log("-" * 60, "heading")

        # Friendly popups
        if ok and not fail:
            messagebox.showinfo(
                "All done!",
                f"{ok} video(s) processed successfully.\n\n"
                f"Saved to:\n{outdir}",
            )
        elif ok and fail:
            messagebox.showwarning(
                "Finished with some problems",
                f"{ok} succeeded, {fail} failed.\n\n"
                "Open 'Show advanced options' → 'Processing log' "
                "for details.",
            )
        elif fail:
            messagebox.showerror(
                "Nothing was processed",
                "None of the videos could be processed.\n\n"
                "Open 'Show advanced options' → 'Processing log' "
                "to see why.",
            )