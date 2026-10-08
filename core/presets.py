# -*- coding: utf-8 -*-
"""Static configuration tables for the formatter."""

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v",
              ".flv", ".wmv", ".mpg", ".mpeg", ".ts", ".3gp"}

PRESETS = {
    "9:16  Vertical Shorts   — 1080 x 1920": (1080, 1920),
    "9:16  Vertical HD       —  720 x 1280": (720, 1280),
    "4:5   Instagram Feed    — 1080 x 1350": (1080, 1350),
    "1:1   Square Feed       — 1080 x 1080": (1080, 1080),
    "16:9  Widescreen        — 1920 x 1080": (1920, 1080),
    "16:9  Widescreen HD     — 1280 x  720": (1280, 720),
}

FIT_PAD  = "Pad  — letterbox, keeps full frame"
FIT_CROP = "Crop — fills frame, zooms in"
FIT_BLUR = "Blur — blurred background fill"

FIT_MODES = [FIT_PAD, FIT_CROP, FIT_BLUR]

POSITIONS = {
    "Top-Left":     lambda m: (f"{m}", f"{m}"),
    "Top-Right":    lambda m: (f"W-w-{m}", f"{m}"),
    "Bottom-Left":  lambda m: (f"{m}", f"H-h-{m}"),
    "Bottom-Right": lambda m: (f"W-w-{m}", f"H-h-{m}"),
    "Center":       lambda m: ("(W-w)/2", "(H-h)/2"),
}

ENC_PRESETS = ["ultrafast", "superfast", "veryfast", "faster", "fast",
               "medium", "slow", "slower"]