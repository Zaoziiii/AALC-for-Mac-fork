"""Capture only a game window, excluding the macOS window shadow."""
import subprocess
import tempfile
from pathlib import Path
from PIL import Image

def capture_window(window_id):
    # Pillow's window= capture includes a shadow and exposes no -o option.
    # Use the same macOS backend explicitly so its pixels match CGWindowBounds.
    with tempfile.TemporaryDirectory(prefix='aalc-capture-') as directory:
        path=Path(directory)/'game.png'
        subprocess.run(['/usr/sbin/screencapture','-x','-o','-l',str(window_id),str(path)],
                       check=True, timeout=10, capture_output=True)
        with Image.open(path) as image:
            return image.convert('RGB')
