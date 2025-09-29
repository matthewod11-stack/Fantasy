"""
Local compositor using ffmpeg to build 1080x1920 MP4s from background, captions, and audio.

Design goals:
- Pure ffmpeg invocation (no network)
- Deterministic output via fixed encoding params
- Minimal external Python deps (uses subprocess)
"""
from __future__ import annotations

import os
import subprocess
from typing import Optional


def compose_video(
    background_image: str,
    audio_wav: str,
    caption_text: Optional[str],
    out_mp4: str,
    duration: Optional[float] = None,
) -> str:
    """Compose an MP4 at 1080x1920 from a single background image, optional
    caption text, and an audio WAV file.

    Returns the path to the output file on success.
    """
    # Ensure inputs exist
    if not os.path.exists(background_image):
        raise FileNotFoundError(background_image)
    if not os.path.exists(audio_wav):
        raise FileNotFoundError(audio_wav)

    # Build ffmpeg filter chain for deterministic scaling/padding and optional caption
    vf_parts = [
        # Scale preserving aspect into target, then pad
        "scale=1080:1920:force_original_aspect_ratio=decrease",
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=#000000",
        "format=yuv420p",
    ]

    if caption_text:
        # Draw centered caption near bottom. Avoid specifying fontfile to keep
        # dependency light; this may use the system default font. Keep box for
        # readability. Escape single quotes inside caption.
        safe = caption_text.replace("'", "\\'")
        draw = (
            "drawtext=text='{}':fontcolor=white:fontsize=48:box=1:boxcolor=0x00000099:".format(safe)
            + "x=(w-text_w)/2:y=h-200"
        )
        vf_parts.append(draw)

    vf = ",".join(vf_parts)

    # Build ffmpeg command
    # -loop 1 input for still image, use shorted with audio via -shortest
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        background_image,
        "-i",
        audio_wav,
        # Encoding options for deterministic-ish output
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-g",
        "25",
        "-keyint_min",
        "25",
        "-sc_threshold",
        "0",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        "-vf",
        vf,
    ]

    # If a duration override is provided, add -t
    if duration is not None:
        cmd.extend(["-t", str(duration)])

    cmd.append(out_mp4)

    # Run command
    subprocess.run(cmd, check=True)

    if not os.path.exists(out_mp4):
        raise RuntimeError("ffmpeg failed to produce output")
    return out_mp4
