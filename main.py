# -*- coding: utf-8 -*-
"""Entry point for the Bulk Video Watermarker & Short-Form Formatter."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _apply_icon(app):
    """Try .ico first (multi-size, best on Windows), then .png."""
    assets = ROOT / "assets"

    # --- Prefer .ico ------------------------------------------------
    ico = assets / "icon.ico"
    if ico.is_file():
        try:
            app.iconbitmap(default=str(ico))
            return "ico"
        except Exception:
            pass

    # --- Fall back to .png ------------------------------------------
    png = assets / "icon.png"
    if png.is_file():
        try:
            from tkinter import PhotoImage
            img = PhotoImage(file=str(png))
            app.iconphoto(True, img)
            app._icon_ref = img   # keep a reference so it isn't GC'd
            return "png"
        except Exception:
            pass

    return None


def main():
    from ui.app import WatermarkerApp
    app = WatermarkerApp()
    used = _apply_icon(app)
    if not used:
        # Silent — no icon file found, just use the Tk default
        pass
    app.mainloop()


if __name__ == "__main__":
    main()