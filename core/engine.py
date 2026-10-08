# -*- coding: utf-8 -*-
"""FFmpeg engine + background render worker."""

import os
import sys
import time
import shutil
import threading
import subprocess
from pathlib import Path

from .presets import (
    FIT_PAD, FIT_CROP, FIT_BLUR, POSITIONS, VIDEO_EXTS
)

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


# --------------------------------------------------------------------------- #
#  Binary discovery + probing
# --------------------------------------------------------------------------- #
def locate_binary(name: str):
    """Search ./bin, then system PATH."""
    exe = name + (".exe" if os.name == "nt" else "")
    here = Path(__file__).resolve().parent.parent
    candidates = [here / "bin" / exe, here / exe]

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, Path(meipass) / "bin" / exe)

    for c in candidates:
        if c.is_file():
            return str(c)
    return shutil.which(name) or shutil.which(exe)


def probe_duration(ffprobe: str, path) -> float:
    """Return duration in seconds or 0.0 on failure."""
    if not ffprobe:
        return 0.0
    try:
        res = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=30,
            creationflags=CREATE_NO_WINDOW,
        )
        return float(res.stdout.strip())
    except Exception:
        return 0.0


def scan_folder(folder, recursive=True):
    """Return sorted list of video paths inside folder."""
    root = Path(folder)
    it = root.rglob("*") if recursive else root.glob("*")
    return sorted(p for p in it
                  if p.is_file() and p.suffix.lower() in VIDEO_EXTS)


# --------------------------------------------------------------------------- #
#  Filter-graph builder
# --------------------------------------------------------------------------- #
def build_filter_chain(out_w, out_h, fit, logo,
                       wm_scale_pct, wm_opacity, wm_pos):
    """
    Returns (filter_complex_string, output_label).
    Stage 1 = reframe → [base]
    Stage 2 = overlay watermark → [vout] (or [base] if no logo)
    """
    margin = max(10, int(min(out_w, out_h) * 0.035))
    parts = []

    # ---------- Stage 1: reframe -------------------------------------------
    if fit == FIT_CROP:
        parts.append(
            f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h},setsar=1[base]"
        )
    elif fit == FIT_BLUR:
        parts.append("[0:v]split=2[bg][fg]")
        parts.append(
            f"[bg]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h},boxblur=luma_radius=28:luma_power=2,setsar=1[bgb]"
        )
        parts.append(
            f"[fg]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
            f"setsar=1[fgs]"
        )
        parts.append("[bgb][fgs]overlay=(W-w)/2:(H-h)/2[base]")
    else:  # FIT_PAD
        parts.append(
            f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
            f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[base]"
        )

    # ---------- Stage 2: watermark -----------------------------------------
    if not logo:
        return ";".join(parts), "[base]"

    wm_w = max(2, int(round(out_w * wm_scale_pct / 100.0)))
    parts.append(
        f"[1:v]scale={wm_w}:-1,format=rgba,"
        f"colorchannelmixer=aa={wm_opacity:.2f}[wm]"
    )
    x_expr, y_expr = POSITIONS[wm_pos](margin)
    parts.append(f"[base][wm]overlay={x_expr}:{y_expr}:format=auto[vout]")
    return ";".join(parts), "[vout]"


def build_command(ffmpeg, src, dst, out_w, out_h, fit, logo,
                  wm_scale, wm_opacity, wm_pos, crf, enc_preset):
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src)]
    if logo:
        cmd += ["-i", str(logo)]

    filt, label = build_filter_chain(
        out_w, out_h, fit, logo, wm_scale, wm_opacity, wm_pos
    )

    cmd += [
        "-filter_complex", filt,
        "-map", label,
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", enc_preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-progress", "pipe:1",
        "-nostats",
        str(dst),
    ]
    return cmd


# --------------------------------------------------------------------------- #
#  Background render worker
# --------------------------------------------------------------------------- #
class RenderWorker(threading.Thread):
    """
    Runs the full batch on a daemon thread.
    Posts messages onto msg_queue as tuples:
        ("log",     text, tag)
        ("progress", pct_float)
        ("status",  text)
        ("done",    ok_count, fail_count, elapsed, outdir)
    """

    def __init__(self, files, outdir, logo, cfg, ffmpeg, ffprobe,
                 msg_queue, cancel_event):
        super().__init__(daemon=True)
        self.files = list(files)
        self.outdir = Path(outdir)
        self.logo = logo
        self.cfg = cfg
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.q = msg_queue
        self.cancel_event = cancel_event
        self.current_proc = None

    # ------------------------------------------------------------------ API
    def cancel(self):
        self.cancel_event.set()
        proc = self.current_proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    # ----------------------------------------------------------------- run
    def run(self):
        total = len(self.files)
        ok = fail = 0
        used_names = set()
        t0 = time.time()

        for i, src in enumerate(self.files):
            if self.cancel_event.is_set():
                self.q.put(("log", "Batch cancelled by user.", "warn"))
                break

            src = Path(src)
            self.q.put(("status", f"Rendering {i+1}/{total} — {src.name}"))
            self.q.put(("log", f"▶ ({i+1}/{total})  {src.name}", "info"))

            dst = self._unique_destination(src, i, used_names)
            duration = probe_duration(self.ffprobe, src)

            cmd = build_command(
                self.ffmpeg, src, dst,
                self.cfg["w"], self.cfg["h"], self.cfg["fit"], self.logo,
                self.cfg["wm_scale"], self.cfg["wm_opacity"], self.cfg["wm_pos"],
                self.cfg["crf"], self.cfg["enc"],
            )

            rc, tail = self._run_ffmpeg(cmd, duration, i, total)

            if self.cancel_event.is_set():
                try:
                    if dst.exists():
                        dst.unlink()
                except OSError:
                    pass
                self.q.put(("log", "   ⨯ aborted, partial file removed.", "warn"))
                break

            if rc == 0:
                ok += 1
                self.q.put(("log", f"   ✓ saved → {dst.name}", "success"))
            else:
                fail += 1
                self.q.put(("log", f"   ✗ FAILED  (ffmpeg exit {rc})", "error"))
                for line in (tail or "").splitlines()[-4:]:
                    self.q.put(("log", f"      {line}", "muted"))

        elapsed = time.time() - t0
        self.q.put(("progress", 100.0))
        self.q.put(("done", ok, fail, elapsed, str(self.outdir)))

    # ------------------------------------------------------------- helpers
    def _unique_destination(self, src, index, used):
        dst = self.outdir / f"{src.stem}{self.cfg['suffix']}.mp4"
        try:
            if dst.resolve() == src.resolve():
                dst = dst.with_name(f"{dst.stem}_wm{dst.suffix}")
        except OSError:
            pass
        key = dst.name.lower()
        if key in used:
            dst = dst.with_name(f"{dst.stem}_{index+1}{dst.suffix}")
            key = dst.name.lower()
        used.add(key)
        return dst

    def _run_ffmpeg(self, cmd, duration, index, total):
        tail = []
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=CREATE_NO_WINDOW,
            )
        except OSError as e:
            return 1, f"Launch failed: {e}"

        self.current_proc = proc

        for raw in proc.stdout:
            if self.cancel_event.is_set():
                try:
                    proc.terminate()
                except Exception:
                    pass
                break

            line = raw.strip()
            if not line:
                continue

            if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
                try:
                    us = int(line.split("=", 1)[1])
                except (ValueError, IndexError):
                    continue
                if duration > 0 and total > 0:
                    frac = min(us / (duration * 1_000_000.0), 1.0)
                    overall = ((index + frac) / total) * 100.0
                    self.q.put(("progress", overall))
            elif line.startswith((
                "frame=", "fps=", "bitrate=", "total_size=", "out_time=",
                "dup_frames=", "drop_frames=", "speed=", "progress=",
                "stream_",
            )):
                continue
            else:
                tail.append(line)
                if len(tail) > 40:
                    tail.pop(0)

        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        self.current_proc = None
        return proc.returncode, "\n".join(tail)