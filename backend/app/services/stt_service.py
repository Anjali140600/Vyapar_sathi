"""
STT Service — CLI-based Whisper transcription.
Ported from step2-multimodal/server/whisperTranscribe.js.

Uses subprocess Whisper CLI (not the in-process whisper package) so it:
  • Works with any Python env / conda setup on Windows
  • Sets PYTHONNOUSERSITE=1 to avoid numpy conflicts (Anaconda + user site-packages)
  • Prepends CONDA_PREFIX/Scripts and VIRTUAL_ENV/Scripts to PATH so whisper.exe is found
  • Falls back through: WHISPER_CMD → conda whisper.exe → `whisper` → python -m whisper
  • Converts any audio to 16 kHz mono WAV via ffmpeg before sending to Whisper
"""

import os
import sys
import uuid
import shutil
import tempfile
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# ── helpers ──────────────────────────────────────────────────────────────────

def _ffmpeg_path() -> str | None:
    """Return path to ffmpeg: prefer PATH; fall back to common Windows locations."""
    from shutil import which
    found = which("ffmpeg")
    if found:
        return found
    # Common install locations on Windows (winget / chocolatey / scoop)
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        os.path.expanduser(r"~\scoop\apps\ffmpeg\current\bin\ffmpeg.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _child_env_base() -> dict:
    """Return os.environ copy with conda/venv Scripts prepended and PYTHONNOUSERSITE=1."""
    env = dict(os.environ)
    env["PYTHONNOUSERSITE"] = "1"

    os_sep = os.pathsep
    front: list[str] = []

    conda = env.get("CONDA_PREFIX", "")
    if conda:
        for sub in ("Scripts", os.path.join("Library", "bin"), "bin"):
            p = os.path.join(conda, sub)
            if p not in front:
                front.append(p)

    venv = env.get("VIRTUAL_ENV", "")
    if venv:
        p = os.path.join(venv, "Scripts")
        if p not in front:
            front.append(p)

    if front:
        env["PATH"] = os_sep.join(front) + os_sep + env.get("PATH", "")

    return env


def _convert_to_wav(input_path: str, wav_path: str) -> None:
    """Convert audio file to 16 kHz mono WAV using ffmpeg."""
    ffmpeg = _ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found. Install it (winget install ffmpeg) or add it to PATH."
        )
    result = subprocess.run(
        [ffmpeg, "-y", "-i", input_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav_path],
        capture_output=True,
        env=_child_env_base(),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg conversion failed:\n{result.stderr.decode(errors='replace')}"
        )


def _whisper_args(wav_path: str, out_dir: str, model: str, fp16: bool) -> list[str]:
    raw_lang = (os.getenv("WHISPER_LANGUAGE") or "en").strip()
    language = None if not raw_lang or raw_lang.lower() == "auto" else raw_lang
    initial_prompt = (os.getenv("WHISPER_INITIAL_PROMPT") or "").strip() or None
    model_dir = (os.getenv("WHISPER_MODEL_DIR") or "").strip() or None

    args = [wav_path, "--model", model, "--output_dir", out_dir, "--output_format", "txt"]
    if not fp16:
        args += ["--fp16", "False"]
    if model_dir:
        args += ["--model_dir", model_dir]
    if language:
        args += ["--language", language]
    if initial_prompt:
        args += ["--initial_prompt", initial_prompt]
    return args


def _build_try_runs(wav_path: str, out_dir: str, model: str, fp16: bool):
    """Build ordered list of (cmd, args) pairs to try for Whisper."""
    args = _whisper_args(wav_path, out_dir, model, fp16)
    mod_args = ["-m", "whisper"] + args

    is_win = sys.platform == "win32"
    conda = (os.getenv("CONDA_PREFIX") or "").strip()
    runs: list[tuple[str, list[str]]] = []

    # 1. WHISPER_CMD (user-supplied full path)
    custom_cmd = (os.getenv("WHISPER_CMD") or "").strip()
    if custom_cmd:
        runs.append((custom_cmd, args))

    # 2. WHISPER_PYTHON (user-supplied python.exe)
    custom_py = (os.getenv("WHISPER_PYTHON") or "").strip()
    if custom_py:
        runs.append((custom_py, mod_args))

    # 3. conda Scripts/whisper.exe (Windows)
    if is_win and conda:
        conda_whisper = os.path.join(conda, "Scripts", "whisper.exe")
        if os.path.isfile(conda_whisper):
            runs.append((conda_whisper, args))

    # 4. `whisper` on PATH
    runs.append(("whisper", args))

    # 5. conda python.exe -m whisper
    if is_win and conda:
        conda_py = os.path.join(conda, "python.exe")
        if os.path.isfile(conda_py):
            runs.append((conda_py, mod_args))

    # 6. py / python -m whisper
    if is_win:
        runs += [("py", mod_args), ("python", mod_args)]
    else:
        runs += [("python3", mod_args), ("python", mod_args), ("py", mod_args)]

    return runs


def _is_disk_full(msg: str) -> bool:
    import re
    return bool(re.search(r"No space left on device|Errno\s*28", msg, re.IGNORECASE))


def _transcribe_with_whisper(wav_path: str, out_dir: str) -> None:
    """Run Whisper CLI; raises RuntimeError on total failure."""
    model = (os.getenv("WHISPER_MODEL") or "base").strip()
    fp16_env = os.getenv("WHISPER_FP16", "")
    fp16 = fp16_env.lower() not in ("", "0", "false") if fp16_env else False

    runs = _build_try_runs(wav_path, out_dir, model, fp16)
    errors: list[str] = []

    env = _child_env_base()
    opts: dict = dict(env=env, capture_output=True)

    for cmd, args in runs:
        try:
            result = subprocess.run([cmd] + args, **opts, timeout=300)
            if result.returncode == 0:
                return
            msg = result.stderr.decode(errors="replace")
            if _is_disk_full(msg):
                raise RuntimeError(
                    "Whisper model download failed (disk full — Errno 28). "
                    "Free at least ~500MB on C:, or set WHISPER_MODEL=tiny (~75MB) in .env, "
                    "or set WHISPER_MODEL_DIR=D:\\some\\folder in .env."
                )
            errors.append(f"{cmd}: {msg[:400]}")
        except FileNotFoundError:
            errors.append(f"{cmd}: not found")
        except subprocess.TimeoutExpired:
            errors.append(f"{cmd}: timed out after 300s")

    hint = (
        " On Windows: set WHISPER_CMD to the full path of whisper.exe "
        "(e.g. under Anaconda Scripts), or set WHISPER_PYTHON to your python.exe."
        if sys.platform == "win32" else ""
    )
    raise RuntimeError(
        f"Whisper failed after {len(runs)} attempts.{hint}\n"
        + "\n".join(errors)
    )


# ── public API ────────────────────────────────────────────────────────────────

class STTService:
    """
    Speech-to-Text service using the Whisper CLI subprocess.
    Converts any supported audio format → 16 kHz WAV → transcript text.
    """

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribes an audio file. Returns transcript string or raises RuntimeError.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        tmp_dir = tempfile.mkdtemp(prefix="vyapar-stt-")
        try:
            base = Path(audio_path).stem
            wav_path = os.path.join(tmp_dir, f"{base}.wav")
            _convert_to_wav(audio_path, wav_path)
            _transcribe_with_whisper(wav_path, tmp_dir)
            txt_path = os.path.join(tmp_dir, f"{base}.txt")
            if not os.path.isfile(txt_path):
                raise RuntimeError("Whisper ran but produced no .txt output file.")
            with open(txt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def transcribe_bytes(self, audio_bytes: bytes, suffix: str = ".webm") -> str:
        """
        Transcribes raw audio bytes (e.g. from browser MediaRecorder).
        """
        tmp_dir = tempfile.mkdtemp(prefix="vyapar-stt-")
        try:
            uid = str(uuid.uuid4())[:8]
            input_path = os.path.join(tmp_dir, f"input_{uid}{suffix}")
            with open(input_path, "wb") as f:
                f.write(audio_bytes)
            return self.transcribe(input_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
