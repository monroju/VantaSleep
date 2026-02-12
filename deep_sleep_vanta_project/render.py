"""
render.py — FFmpeg Video Rendering Pipeline for Deep Sleep Vanta Project

Creates a True Black (#000000) 4K video with the layered audio track.
  - Resolution: 3840x2160
  - Codec: H.264 (libx264) with very low video bitrate (static frame)
  - Audio: AAC 320 kbps
  - Efficient: uses a single black frame looped to the target duration
"""

import os
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


def generate_black_frame(output_path: str, width: int = 3840, height: int = 2160) -> str:
    """Use FFmpeg to create a single black PNG frame at the target resolution."""
    ffmpeg = _find_ffmpeg()
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={width}x{height}:d=1:r=1",
        "-frames:v", "1",
        output_path,
    ]
    print(f"[render] Generating black frame → {output_path}")
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def render_video(
    audio_path: str,
    output_path: str,
    duration_sec: float,
    width: int = 3840,
    height: int = 2160,
    video_bitrate: str = "2M",
    audio_bitrate: str = "320k",
    codec: str = "libx264",
) -> str:
    """
    Stitch a looped black frame with the audio track into the final video.

    Uses FFmpeg's loop + shortest strategy:
      - loop a single black frame for the duration of the audio
      - mux the pre-rendered audio
      - encode with H.264/HEVC at low video bitrate
    """
    ffmpeg = _find_ffmpeg()

    # Build the frame path next to audio
    frame_dir = os.path.dirname(audio_path) or "."
    frame_path = os.path.join(frame_dir, "black_frame.png")
    generate_black_frame(frame_path, width, height)

    fps = 1  # 1 fps is enough for a static image — minimal file size

    cmd = [
        ffmpeg, "-y",
        # Video input: loop the single black frame
        "-loop", "1",
        "-framerate", str(fps),
        "-i", frame_path,
        # Audio input
        "-i", audio_path,
        # Map both streams
        "-map", "0:v:0",
        "-map", "1:a:0",
        # Video encoding
        "-c:v", codec,
        "-preset", "ultrafast",
        "-tune", "stillimage",
        "-b:v", video_bitrate,
        "-pix_fmt", "yuv420p",
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
    print(f"[render] Codec={codec}  Video={video_bitrate}  Audio={audio_bitrate}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("[render] FFmpeg stderr:\n", result.stderr[-2000:] if result.stderr else "(empty)")
        result.check_returncode()  # raise CalledProcessError

    print(f"[render] Done → {output_path}")
    return output_path
