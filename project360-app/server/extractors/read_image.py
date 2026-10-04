"""Local OCR: Apple Vision on macOS; Tesseract on other supported hosts."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from threading import Lock

_compile_lock = Lock()


def _vision_binary():
    source = Path(__file__).with_name("vision_ocr.swift")
    stamp = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    cache = Path(tempfile.gettempdir()) / "nova-ocr"
    cache.mkdir(exist_ok=True)
    binary = cache / f"vision-{stamp}"
    with _compile_lock:
        if not binary.exists():
            subprocess.run(["swiftc", "-module-cache-path", str(cache / "modules"), str(source), "-o", str(binary)],
                           check=True, capture_output=True, timeout=120)
    return str(binary)


def read_image(path):
    if sys.platform == "darwin" and shutil.which("swiftc"):
        command = [_vision_binary(), str(path)]
    elif shutil.which("tesseract") and Path(path).suffix.lower() != ".pdf":
        languages = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=10).stdout
        command = ["tesseract", str(path), "stdout", "-l", "fra+eng" if "fra" in languages else "eng"]
    else:
        raise ValueError("OCR local indisponible. Ajoutez une transcription dans l'aperçu (ou installez Tesseract pour les images).")
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=90)
    return result.stdout.strip()
