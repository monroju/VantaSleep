"""
generator.py — Audio Synthesis Engine for Deep Sleep Vanta Project

Generates scientifically layered audio:
  1. Synthetic rain (pink-noise-based) or loads rain_source.wav
  2. Brown noise floor for low-frequency masking
  3. Delta-wave binaural beats (200 Hz left / 204 Hz right → 4 Hz delta)
  4. Seamless 10-second crossfade looping
"""

import os
import numpy as np
from pydub import AudioSegment

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SAMPLE_RATE = 44100
CHANNELS = 2
SAMPLE_WIDTH = 2  # 16-bit

# Binaural beat parameters
LEFT_FREQ = 200.0   # Hz
RIGHT_FREQ = 204.0  # Hz  (204 - 200 = 4 Hz delta wave)

# Volume mix (dBFS offsets applied after normalisation)
RAIN_VOLUME_DB = -6
BROWN_NOISE_VOLUME_DB = -18
BINAURAL_VOLUME_DB = -20

CROSSFADE_SEC = 10  # seconds of overlap for seamless loop


# ---------------------------------------------------------------------------
# Waveform helpers
# ---------------------------------------------------------------------------

def _seconds_to_samples(seconds: float) -> int:
    return int(seconds * SAMPLE_RATE)


def _normalize(arr: np.ndarray) -> np.ndarray:
    """Normalise a float array to [-1, 1]."""
    peak = np.max(np.abs(arr))
    if peak == 0:
        return arr
    return arr / peak


def _float_to_int16(arr: np.ndarray) -> np.ndarray:
    return (arr * 32767).astype(np.int16)


def _mono_array_to_segment(arr: np.ndarray) -> AudioSegment:
    """Convert a mono float64 numpy array to a pydub AudioSegment."""
    pcm = _float_to_int16(_normalize(arr))
    return AudioSegment(
        pcm.tobytes(),
        frame_rate=SAMPLE_RATE,
        sample_width=SAMPLE_WIDTH,
        channels=1,
    )


def _stereo_arrays_to_segment(left: np.ndarray, right: np.ndarray) -> AudioSegment:
    """Convert separate L/R float64 arrays to a stereo AudioSegment."""
    left_norm = _normalize(left)
    right_norm = _normalize(right)
    interleaved = np.empty(len(left_norm) + len(right_norm), dtype=np.float64)
    interleaved[0::2] = left_norm
    interleaved[1::2] = right_norm
    pcm = _float_to_int16(interleaved)
    return AudioSegment(
        pcm.tobytes(),
        frame_rate=SAMPLE_RATE,
        sample_width=SAMPLE_WIDTH,
        channels=2,
    )


# ---------------------------------------------------------------------------
# Noise generators
# ---------------------------------------------------------------------------

def generate_pink_noise(duration_sec: float) -> np.ndarray:
    """Generate pink (1/f) noise via the Voss-McCartney algorithm."""
    n_samples = _seconds_to_samples(duration_sec)
    num_rows = 16
    array = np.random.randn(num_rows, n_samples)
    # cumulative row contribution
    out = np.zeros(n_samples, dtype=np.float64)
    for i in range(num_rows):
        step = 2 ** i
        row = np.repeat(array[i, ::step], step)[:n_samples]
        out += row
    return _normalize(out)


def generate_brown_noise(duration_sec: float) -> np.ndarray:
    """Generate brown noise (random walk, then normalise)."""
    n_samples = _seconds_to_samples(duration_sec)
    white = np.random.randn(n_samples)
    brown = np.cumsum(white)
    return _normalize(brown)


def generate_sine(freq: float, duration_sec: float) -> np.ndarray:
    """Generate a pure sine wave at *freq* Hz."""
    n_samples = _seconds_to_samples(duration_sec)
    t = np.arange(n_samples) / SAMPLE_RATE
    return np.sin(2.0 * np.pi * freq * t)


# ---------------------------------------------------------------------------
# Synthetic rain
# ---------------------------------------------------------------------------

def generate_synthetic_rain(duration_sec: float) -> AudioSegment:
    """Create a rain-like texture from filtered pink noise (mono → stereo)."""
    pink = generate_pink_noise(duration_sec)
    # Gentle low-pass effect by averaging neighbours
    kernel_size = 5
    kernel = np.ones(kernel_size) / kernel_size
    rain = np.convolve(pink, kernel, mode="same")
    seg = _mono_array_to_segment(rain)
    # Make stereo
    seg = AudioSegment.from_mono_audiosegments(seg, seg)
    return seg


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_or_generate_rain(duration_sec: float, rain_path: str = "rain_source.wav") -> AudioSegment:
    """Load rain_source.wav if present; otherwise synthesise a substitute."""
    if os.path.isfile(rain_path):
        print(f"[generator] Loading rain from {rain_path}")
        rain = AudioSegment.from_wav(rain_path)
        # Ensure stereo
        if rain.channels == 1:
            rain = AudioSegment.from_mono_audiosegments(rain, rain)
        # Loop / trim to target duration
        target_ms = int(duration_sec * 1000)
        if len(rain) < target_ms:
            repeats = (target_ms // len(rain)) + 1
            rain = rain * repeats
        rain = rain[:target_ms]
    else:
        print("[generator] rain_source.wav not found — generating synthetic rain")
        rain = generate_synthetic_rain(duration_sec)
    return rain


def generate_brown_noise_layer(duration_sec: float) -> AudioSegment:
    """Return a stereo brown-noise AudioSegment."""
    brown = generate_brown_noise(duration_sec)
    seg = _mono_array_to_segment(brown)
    seg = AudioSegment.from_mono_audiosegments(seg, seg)
    return seg


def generate_binaural_layer(duration_sec: float) -> AudioSegment:
    """Return a stereo binaural-beat AudioSegment (200 Hz L / 204 Hz R)."""
    left = generate_sine(LEFT_FREQ, duration_sec)
    right = generate_sine(RIGHT_FREQ, duration_sec)
    return _stereo_arrays_to_segment(left, right)


def mix_audio(duration_sec: float, rain_path: str = "rain_source.wav") -> AudioSegment:
    """
    Build the full audio mix for *duration_sec*:
      rain  +  brown noise  +  binaural beats
    with volume adjustments and a seamless crossfade loop.
    """
    # We generate a "segment" slightly longer than needed so we can crossfade
    segment_sec = duration_sec + CROSSFADE_SEC
    print(f"[generator] Generating rain layer ({segment_sec:.0f}s) ...")
    rain = load_or_generate_rain(segment_sec, rain_path)
    rain = rain + RAIN_VOLUME_DB

    print(f"[generator] Generating brown noise layer ({segment_sec:.0f}s) ...")
    brown = generate_brown_noise_layer(segment_sec)
    brown = brown + BROWN_NOISE_VOLUME_DB

    print(f"[generator] Generating binaural layer ({segment_sec:.0f}s) ...")
    binaural = generate_binaural_layer(segment_sec)
    binaural = binaural + BINAURAL_VOLUME_DB

    # Overlay all layers
    print("[generator] Mixing layers ...")
    mixed = rain.overlay(brown).overlay(binaural)

    # Seamless crossfade: take the tail, crossfade it with the head
    crossfade_ms = CROSSFADE_SEC * 1000
    target_ms = int(duration_sec * 1000)

    head = mixed[:target_ms]
    tail = mixed[target_ms : target_ms + crossfade_ms]

    # Apply crossfade at the boundary (end of head ← tail)
    print(f"[generator] Applying {CROSSFADE_SEC}s crossfade for seamless loop ...")
    final = head.fade_out(crossfade_ms).overlay(
        tail.fade_in(crossfade_ms),
        position=target_ms - crossfade_ms,
    )

    return final


def export_audio(audio: AudioSegment, path: str) -> str:
    """Export the mixed audio to a WAV file and return the path."""
    audio.export(path, format="wav")
    print(f"[generator] Audio exported → {path}")
    return path
