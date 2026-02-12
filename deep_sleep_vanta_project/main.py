#!/usr/bin/env python3
"""
main.py — Orchestrator for Deep Sleep Vanta Project

Usage:
    python main.py                   # Full 8-hour render
    python main.py --test            # 1-minute test sample
    python main.py --duration 300    # Custom duration in seconds

Output lands in the ./output/ folder.
"""

import argparse
import os
import time

from generator import mix_audio, export_audio
from render import render_video

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
FULL_DURATION_SEC = 8 * 60 * 60        # 8 hours
TEST_DURATION_SEC = 60                  # 1 minute
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
# Rain audio source: "Relaxing Sound of Rain Puddles Light Rain and Rain Drops Falling"
# YouTube reference: https://youtube.com/shorts/Go6vFy7LK5Y
RAIN_SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "rain_puddles.wav")


def run(duration_sec: float, output_dir: str, rain_path: str) -> str:
    os.makedirs(output_dir, exist_ok=True)

    tag = "test" if duration_sec <= TEST_DURATION_SEC else "full"
    audio_path = os.path.join(output_dir, f"deep_sleep_audio_{tag}.wav")
    video_path = os.path.join(output_dir, f"deep_sleep_vanta_{tag}.mp4")

    t0 = time.time()

    # --- Step 1: Audio synthesis ---
    print("=" * 60)
    print(f"  Deep Sleep Vanta — Audio Synthesis  ({duration_sec:.0f}s)")
    print("=" * 60)
    audio = mix_audio(duration_sec, rain_path=rain_path)
    export_audio(audio, audio_path)

    # --- Step 2: Video rendering ---
    print()
    print("=" * 60)
    print(f"  Deep Sleep Vanta — Video Render  ({duration_sec:.0f}s)")
    print("=" * 60)
    render_video(
        audio_path=audio_path,
        output_path=video_path,
        duration_sec=duration_sec,
    )

    elapsed = time.time() - t0
    minutes = elapsed / 60

    print()
    print("=" * 60)
    print(f"  COMPLETE — {video_path}")
    print(f"  Elapsed: {minutes:.1f} min")
    print("=" * 60)

    return video_path


def main():
    parser = argparse.ArgumentParser(description="Deep Sleep Vanta Video Generator")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Generate a 1-minute test sample instead of the full 8-hour video",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Custom duration in seconds (overrides --test and default 8h)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--rain",
        type=str,
        default=RAIN_SOURCE,
        help="Path to rain audio WAV file (synthetic substitute used if missing)",
    )
    args = parser.parse_args()

    if args.duration is not None:
        duration = args.duration
    elif args.test:
        duration = TEST_DURATION_SEC
    else:
        duration = FULL_DURATION_SEC

    run(duration, args.output_dir, args.rain)


if __name__ == "__main__":
    main()
