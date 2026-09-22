# Step 2 — Multimodal input (free: Whisper + Tesseract)

Separate from Step 1 (transactions). Converts:

- **Text** → same text (pass-through)
- **Voice** → text via **OpenAI Whisper** (local CLI, no API key)
- **Image** → text via **Tesseract.js** (bundled, downloads language data on first use)

## Prerequisites (voice)

1. **Python 3** installed.
2. Install Whisper:

   ```bash
   pip install openai-whisper
   ```

3. **ffmpeg:** You do **not** need `ffmpeg` in your system PATH. The app prepends the bundled `ffmpeg-static` binary to the Whisper process `PATH`, so Whisper can find `ffmpeg` automatically.

4. Check in a terminal:

   ```bash
   whisper --help
   ```

   If that fails, try:

   ```bash
   python -m whisper --help
   ```

   On Windows you can set in `.env`:

   ```env
   WHISPER_CMD=C:\Path\To\Python\Scripts\whisper.exe
   ```

## Setup

1. Copy `.env.example` to `.env`
2. `npm install`
3. `npm start`
4. Open `http://localhost:3100`

The voice section supports **in-browser recording** (microphone) as well as file upload. Audio is sent to your machine and transcribed with **local Whisper** (same as uploads).

## Environment

| Variable | Meaning |
|----------|---------|
| `PORT` | Server port (default 3100) |
| `TESSERACT_LANGS` | e.g. `eng`, `hin`, `eng+hin` |
| `WHISPER_MODEL` | `tiny` … `large` (default **`base`** in code; use **`tiny`** if disk is full) |
| `WHISPER_MODEL_DIR` | Folder for Whisper model downloads (if your main drive is full, use another drive) |
| `WHISPER_CMD` | Optional full path to `whisper` if not on PATH |
| `WHISPER_PYTHON` | Optional full path to `python.exe` with Whisper installed (Windows: avoids `python3` / PATH issues) |
| `CONDA_PREFIX` | Optional conda base path (`conda info --base`) so Node finds `Scripts\whisper.exe` when the IDE does not inherit conda PATH |
| `WHISPER_FP16` | Set `false` on CPU if needed |
| `WHISPER_LANGUAGE` | e.g. `en` or `hi` — **recommended** for live mic (avoids wrong language on short clips). Use `auto` to let Whisper guess. |
| `WHISPER_INITIAL_PROMPT` | Optional short text to bias transcription (e.g. English + Indian names) |

## API

- `POST /api/input/text` — JSON `{ "text": "..." }`
- `POST /api/input/voice` — form field `audio`
- `POST /api/input/image` — form field `image`
- `GET /api/health`

## Windows: `unrecognized arguments: speech, Indian names`

That happens when `--initial_prompt` contains spaces and the process was started with `cmd.exe` in a way that splits the text. This project runs Whisper **without** the shell so the full prompt is one argument. If you still see issues, shorten `WHISPER_INITIAL_PROMPT` or remove it ( `--language en` is usually enough).

## Disk full (Errno 28) when downloading Whisper models

Whisper downloads models on first use. If you see `No space left on device`:

1. Free space on the drive that holds the cache (often `C:`), **or** set `WHISPER_MODEL_DIR` to a folder on another drive with space (create the folder first).
2. Use a smaller model: `WHISPER_MODEL=tiny` in `.env` (~75MB vs ~460MB for `small`).
3. Remove a partial download if needed: your user `.cache` folder (Whisper stores under the cache root for your Python install).

## Troubleshooting (Windows + Anaconda)

If `whisper --help` fails with `No module named 'numpy._utils'`, Python is mixing **Anaconda** with a separate **user** site-packages folder (often `%APPDATA%\Python\Python313`).

The Step 2 server sets **`PYTHONNOUSERSITE=1`** when it runs Whisper so that mix is ignored.

**Test in PowerShell:**

```powershell
$env:PYTHONNOUSERSITE = "1"
whisper --help
```

If it still fails, repair packages inside the environment you use for Whisper:

```powershell
conda activate base
pip install -U "numpy>=2"
pip install -U openai-whisper
```
