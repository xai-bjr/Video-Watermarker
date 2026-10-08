# -*- coding: utf-8 -*-
"""
Project self-check + auto-launch
================================
Runs a full diagnostic of the Bulk Video Watermarker project:
  1. Python version
  2. Folder structure
  3. File sizes (empty files flagged)
  4. Module imports (syntax + import errors caught)
  5. tkinter availability
  6. FFmpeg / FFprobe presence
  7. Virtual environment

If everything passes, it launches main.py.
Otherwise it prints a detailed report and exits without launching.

Usage:
    ".venv\Scripts\python.exe" selfcheck.py
    (or double-click selfcheck.bat)
"""

import os
import sys
import importlib
import subprocess
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------- colors --
# Enable ANSI colors on Windows CMD
if os.name == "nt":
    os.system("")

class C:
    OK   = "\033[92m"      # green
    FAIL = "\033[91m"      # red
    WARN = "\033[93m"      # yellow
    INFO = "\033[96m"      # cyan
    DIM  = "\033[90m"      # grey
    BOLD = "\033[1m"
    END  = "\033[0m"

PASS = f"{C.OK}[PASS]{C.END}"
FAIL = f"{C.FAIL}[FAIL]{C.END}"
WARN = f"{C.WARN}[WARN]{C.END}"
INFO = f"{C.INFO}[INFO]{C.END}"

# ---------------------------------------------------------------- state --
class Report:
    def __init__(self):
        self.errors   = []
        self.warnings = []
        self.info     = []

    def ok(self, msg):
        print(f"{PASS} {msg}")

    def fail(self, msg):
        print(f"{FAIL} {msg}")
        self.errors.append(msg)

    def warn(self, msg):
        print(f"{WARN} {msg}")
        self.warnings.append(msg)

    def note(self, msg):
        print(f"{INFO} {msg}")
        self.info.append(msg)


R = Report()


# ---------------------------------------------------------------- helpers --
def check_python_version():
    print(f"\n{C.BOLD}=== 1. Python Runtime ==={C.END}")
    ver = sys.version_info
    print(f"      Python {ver.major}.{ver.minor}.{ver.micro}  ({sys.executable})")
    if ver < (3, 8):
        R.fail(f"Python {ver.major}.{ver.minor} is too old (need 3.8+)")
    else:
        R.ok(f"Python {ver.major}.{ver.minor}.{ver.micro}")


def check_folder_structure():
    print(f"\n{C.BOLD}=== 2. Folder Structure ==={C.END}")
    required_dirs = ["core", "ui", "bin", "assets", "output"]
    for d in required_dirs:
        p = ROOT / d
        if p.is_dir():
            R.ok(f"Folder  {d}\\")
        else:
            R.fail(f"Missing folder: {d}\\")

    # .venv (optional — only if present)
    venv = ROOT / ".venv"
    if venv.is_dir():
        R.ok(f"Virtual environment  .venv\\")
    else:
        R.warn("No .venv — run setup.bat first (only needed for run.bat)")


def check_files_exist_and_nonempty():
    print(f"\n{C.BOLD}=== 3. Source Files ==={C.END}")
    required_files = [
        "main.py",
        "requirements.txt",
        "setup.bat",
        "run.bat",
        "core\\__init__.py",
        "core\\presets.py",
        "core\\engine.py",
        "ui\\__init__.py",
        "ui\\theme.py",
        "ui\\widgets.py",
        "ui\\app.py",
    ]
    for rel in required_files:
        p = ROOT / rel
        if not p.is_file():
            R.fail(f"Missing file: {rel}")
        elif p.stat().st_size == 0:
            R.fail(f"Empty file:   {rel}  (0 bytes — needs code)")
        else:
            size = p.stat().st_size
            R.ok(f"{rel:<22}  {size:>7,} bytes")


def check_binaries():
    print(f"\n{C.BOLD}=== 4. FFmpeg Binaries ==={C.END}")
    for name in ("ffmpeg.exe", "ffprobe.exe"):
        p = ROOT / "bin" / name
        if p.is_file() and p.stat().st_size > 1_000_000:
            size_mb = p.stat().st_size / 1_048_576
            R.ok(f"bin\\{name}  ({size_mb:.1f} MB)")
        elif p.is_file():
            R.warn(f"bin\\{name} exists but looks tiny (may be a stub)")
        else:
            R.warn(f"bin\\{name} missing — will try system PATH")


def check_tkinter():
    print(f"\n{C.BOLD}=== 5. Tkinter ==={C.END}")
    try:
        import tkinter
        # Try to actually initialize Tcl/Tk
        root = tkinter.Tk()
        root.withdraw()
        root.destroy()
        R.ok(f"tkinter {tkinter.TkVersion} working")
    except ImportError as e:
        R.fail(f"tkinter not available: {e}")
    except Exception as e:
        R.fail(f"tkinter failed to start: {e}")


def check_pillow():
    print(f"\n{C.BOLD}=== 6. Optional Dependencies ==={C.END}")
    try:
        import PIL
        R.ok(f"Pillow {PIL.__version__}")
    except ImportError:
        R.warn("Pillow not installed (only needed for icon.png)")

    try:
        import darkdetect
        R.ok("darkdetect available")
    except ImportError:
        R.warn("darkdetect not installed (optional)")


def check_imports():
    print(f"\n{C.BOLD}=== 7. Module Imports ==={C.END}")

    modules = [
        ("core",           "core"),
        ("core.presets",   "core.presets"),
        ("core.engine",    "core.engine"),
        ("ui",             "ui"),
        ("ui.theme",       "ui.theme"),
        ("ui.widgets",     "ui.widgets"),
        ("ui.app",         "ui.app"),
    ]

    for label, modname in modules:
        try:
            # Force reload in case of stale bytecode
            if modname in sys.modules:
                del sys.modules[modname]
            importlib.import_module(modname)
            R.ok(f"import {modname}")
        except SyntaxError as e:
            R.fail(f"SYNTAX ERROR in {modname}  line {e.lineno}: {e.msg}")
            R.note(f"   file: {e.filename}")
        except ImportError as e:
            R.fail(f"IMPORT ERROR in {modname}: {e}")
        except Exception as e:
            R.fail(f"ERROR importing {modname}: {type(e).__name__}: {e}")
            R.note("   " + traceback.format_exc().splitlines()[-2])


def check_engine_functions():
    print(f"\n{C.BOLD}=== 8. Engine Sanity ==={C.END}")
    try:
        from core.engine import locate_binary, build_filter_chain, build_command
        from core.presets import FIT_PAD, FIT_CROP, FIT_BLUR

        ffmpeg  = locate_binary("ffmpeg")
        ffprobe = locate_binary("ffprobe")

        if ffmpeg:
            R.ok(f"locate_binary('ffmpeg')  ->  {ffmpeg}")
        else:
            R.fail("locate_binary('ffmpeg') returned None")

        if ffprobe:
            R.ok(f"locate_binary('ffprobe') ->  {ffprobe}")
        else:
            R.warn("locate_binary('ffprobe') returned None (progress bar limited)")

        # Filter graph for each fit mode
        for fit in (FIT_PAD, FIT_CROP, FIT_BLUR):
            try:
                filt, label = build_filter_chain(
                    1080, 1920, fit, "logo.png", 15.0, 0.85, "Bottom-Right"
                )
                if "[base]" in filt or "[vout]" in filt:
                    R.ok(f"build_filter_chain  {fit.split('—')[0].strip()}")
                else:
                    R.fail(f"build_filter_chain produced no labels for {fit}")
            except Exception as e:
                R.fail(f"build_filter_chain error ({fit}): {e}")

        # Full command
        try:
            cmd = build_command(
                ffmpeg or "ffmpeg", "in.mp4", "out.mp4",
                1080, 1920, FIT_PAD, "logo.png",
                15.0, 0.85, "Bottom-Right", 23, "veryfast",
            )
            assert "-filter_complex" in cmd
            assert "libx264" in cmd
            R.ok("build_command produces valid argv")
        except Exception as e:
            R.fail(f"build_command error: {e}")

    except Exception as e:
        R.fail(f"Could not import engine: {e}")


def check_ffmpeg_runs():
    print(f"\n{C.BOLD}=== 9. FFmpeg Executable Test ==={C.END}")
    try:
        from core.engine import locate_binary
        ffmpeg = locate_binary("ffmpeg")
        if not ffmpeg:
            R.warn("Skipping — no ffmpeg found")
            return

        try:
            result = subprocess.run(
                [ffmpeg, "-version"],
                capture_output=True, text=True, timeout=15,
            )
            first_line = result.stdout.splitlines()[0] if result.stdout else "(no output)"
            if result.returncode == 0:
                R.ok(f"ffmpeg -version  ->  {first_line[:70]}")
            else:
                R.fail(f"ffmpeg -version exit code {result.returncode}")
        except subprocess.TimeoutExpired:
            R.fail("ffmpeg -version timed out (15s)")
        except Exception as e:
            R.fail(f"ffmpeg failed to launch: {e}")
    except Exception as e:
        R.fail(f"Could not test ffmpeg: {e}")


# ---------------------------------------------------------------- summary --
def print_summary():
    print(f"\n{C.BOLD}=== SUMMARY ==={C.END}")
    n_err = len(R.errors)
    n_warn = len(R.warnings)

    if n_err == 0 and n_warn == 0:
        print(f"{C.OK}{C.BOLD}  ✓ ALL CHECKS PASSED — everything looks perfect!{C.END}")
    elif n_err == 0:
        print(f"{C.OK}{C.BOLD}  ✓ ALL CRITICAL CHECKS PASSED{C.END}")
        print(f"{C.WARN}  ⚠  {n_warn} warning(s) — see above{C.END}")
    else:
        print(f"{C.FAIL}{C.BOLD}  ✗ {n_err} ERROR(S) — fix these before launching:{C.END}")
        for i, e in enumerate(R.errors, 1):
            print(f"{C.FAIL}     {i}. {e}{C.END}")
        if n_warn:
            print(f"{C.WARN}  ⚠  plus {n_warn} warning(s){C.END}")

    return n_err == 0


# ---------------------------------------------------------------- launch --
def launch_app():
    print(f"\n{C.BOLD}=== LAUNCHING APPLICATION ==={C.END}")
    print(f"{C.INFO}  Running main.py ...{C.END}\n")
    try:
        from ui.app import WatermarkerApp
        app = WatermarkerApp()
        try:
            icon = ROOT / "assets" / "icon.png"
            if icon.is_file():
                from tkinter import PhotoImage
                app.iconphoto(True, PhotoImage(file=str(icon)))
        except Exception:
            pass
        app.mainloop()
    except Exception:
        print(f"\n{C.FAIL}{C.BOLD}Application crashed during startup:{C.END}")
        traceback.print_exc()
        return False
    return True


# ------------------------------------------------------------------ main --
def main():
    banner = "=" * 62
    print(f"{C.BOLD}{C.INFO}")
    print(banner)
    print("   BULK VIDEO WATERMARKER  -  SELF-CHECK & LAUNCH")
    print(f"   Project: {ROOT}")
    print(banner)
    print(f"{C.END}")

    check_python_version()
    check_folder_structure()
    check_files_exist_and_nonempty()
    check_binaries()
    check_tkinter()
    check_pillow()
    check_imports()
    check_engine_functions()
    check_ffmpeg_runs()

    ok = print_summary()

    if not ok:
        print(f"\n{C.FAIL}  Launch aborted. Fix the errors above and re-run.{C.END}")
        print(f"{C.DIM}  Tip: run this same script again after fixing.{C.END}")
        sys.exit(1)

    # Ask whether to launch
    print()
    try:
        answer = input(f"{C.BOLD}Launch the application now? [Y/n] {C.END}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "y"

    if answer in ("", "y", "yes"):
        launch_app()
    else:
        print(f"{C.INFO}  Skipped launch.{C.END}")


if __name__ == "__main__":
    main()