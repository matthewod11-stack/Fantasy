import json

from apps.batch.runner import run_local_render_for_week


def test_local_compositor_creates_mp4(tmp_path, monkeypatch):
    # Prepare out/week-1 with a manifest entry
    out_dir = tmp_path / "week-1"
    out_dir.mkdir(parents=True)

    # Create a dummy markdown path
    md = out_dir / "PlayerA__start-sit.md"
    md.write_text("Test content", encoding="utf-8")

    entries = [{"player": "PlayerA", "week": 1, "kind": "start-sit", "path": md.name}]
    manifest = out_dir / "manifest.json"
    manifest.write_text(json.dumps(entries), encoding="utf-8")

    # Create a simple background PPM (portable pixmap) 1080x1920 black
    bg = out_dir / "background.jpg"
    # Use ffmpeg to produce a background if available; otherwise create a small PPM and rely on ffmpeg in compositor
    # We'll just create a tiny PNG using Pillow if available, else fallback to a PPM
    try:
        from PIL import Image

        im = Image.new("RGB", (1080, 1920), color=(0, 0, 0))
        im.save(str(bg))
    except Exception:
        # write a simple PPM
        ppm = out_dir / "background.ppm"
        with ppm.open("wb") as f:
            f.write(b"P6\n1080 1920\n255\n")
            f.write(b"\x00\x00\x00" * 1080 * 1920)
        # convert ppm to jpg using ffmpeg
        import subprocess

        subprocess.run(["ffmpeg", "-y", "-f", "image2", "-i", str(ppm), str(bg)], check=False)

    # Create a 2s wav audio
    audio = out_dir / "PlayerA__start-sit.wav"
    try:
        import wave
        import struct

        with wave.open(str(audio), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            frames = b"".join([struct.pack("h", 0) for _ in range(16000 * 2)])
            wf.writeframes(frames)
    except Exception:
        pass

    # Run local renderer
    run_local_render_for_week(1, out_root=str(tmp_path))

    out_mp4 = out_dir / "videos" / "PlayerA__start-sit.mp4"
    assert out_mp4.exists()
