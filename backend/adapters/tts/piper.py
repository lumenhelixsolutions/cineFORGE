"""Local Piper TTS adapter."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)


class PiperTTS:
    """CPU-based local TTS via Piper."""

    def __init__(self, voice_model: str | None = None) -> None:
        self.provider_id = "piper.local"
        self.is_local = True
        self._voice_model = voice_model or "en_US-lessac-medium"

    async def synthesize(self, text: str, voice: str, out: Path) -> Path:
        cmd = [
            "piper",
            "--model",
            self._voice_model,
            "--output_file",
            str(out),
        ]
        try:
            subprocess.run(
                cmd,
                input=text.encode(),
                capture_output=True,
                check=True,
            )
            logger.info("Piper TTS wrote %s", out)
            return out
        except FileNotFoundError:
            raise RuntimeError("piper binary not found in PATH")
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Piper TTS failed: {exc.stderr.decode()}")
