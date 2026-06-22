import subprocess
from pathlib import Path

CAPTURE_PATH = "/tmp/sinergi_capture.jpg"


def capture_photo() -> str:
    cmd = [
        "rpicam-still",
        "--output", CAPTURE_PATH,
        "--width",  "1280",
        "--height", "960",
        "--timeout", "2000",
        "--nopreview",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        raise RuntimeError(f"Camera error: {r.stderr.strip() or r.stdout.strip()}")
    if not Path(CAPTURE_PATH).exists():
        raise RuntimeError("Output kamera tidak ditemukan.")
    return CAPTURE_PATH
