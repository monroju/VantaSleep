"""
render.py — FFmpeg Video Rendering Pipeline for Deep Sleep Vanta Project

Creates a True Black (#000000) 4K video with the layered audio track.
  - Resolution: 3840x2160
  - Codec: H.264 (libx264), CRF 18, tune stillimage
  - Full Range (PC Range) colour to guarantee absolute 0 on OLED panels
  - BT.709 colourspace / primaries / transfer characteristics
  - Audio: AAC 320 kbps
  - Uses lavfi color source at 24 fps — no intermediate PNG needed
"""

import subprocess
import shutil


def _find_ffmpeg() -> str:
    """Return the path to ffmpeg or raise."""
    path = shutil.which("ffmpeg")
    if path is None:
        raise FileNotFoundError(
            "ffmpeg not found on PATH. Install it with: apt install ffmpeg"
        )
    return path


def render_video(
    audio_path: str,
    output_path: str,
    duration_sec: float,
    width: int = 3840,
    height: int = 2160,
    audio_bitrate: str = "320k",
) -> str:
    """
    Generate a True Black 4K video with the audio track.

    Uses FFmpeg lavfi color source at 24 fps directly (no intermediate frame).
    Full Range (PC Range) + BT.709 metadata ensures absolute 0 on OLED panels.
    CRF 18 avoids any compression artefacts in the black.
    """
    ffmpeg = _find_ffmpeg()

    cmd = [
        ffmpeg, "-y",
        # Video input: lavfi black colour source at 24 fps
        "-f", "lavfi",
        "-i", f"color=c=black:s={width}x{height}:r=24",
        # Audio input
        "-i", audio_path,
        # Video filter: force full range and pixel format
        "-vf", "scale=in_range=full:out_range=full,format=yuv420p",
        # Video encoding
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-crf", "18",
        # Full Range (PC Range) + BT.709 colour metadata
        "-color_range", "pc",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        # Audio encoding
        "-c:a", "aac",
        "-b:a", audio_bitrate,
        # Duration control: stop at the shortest stream (audio)
        "-shortest",
        "-t", str(int(duration_sec)),
        # Faststart for YouTube streaming
        "-movflags", "+faststart",
        output_path,
    ]

    print(f"[render] Encoding video ({duration_sec:.0f}s) → {output_path}")
    print(f"[render] CRF=18  Full Range (PC)  BT.709  Audio={audio_bitrate}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("[render] FFmpeg stderr:\n", result.stderr[-2000:] if result.stderr else "(empty)")
        result.check_returncode()  # raise CalledProcessError

    print(f"[render] Done → {output_path}")
    return output_path
