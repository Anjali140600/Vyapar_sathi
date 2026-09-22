require("dotenv").config();
const fs = require("fs/promises");
const path = require("path");
const crypto = require("crypto");
const os = require("os");
const express = require("express");
const cors = require("cors");
const multer = require("multer");
const { createWorker } = require("tesseract.js");
const { transcribeAudioFile } = require("./whisperTranscribe");

const app = express();
const PORT = Number(process.env.PORT) || 3100;
const TESSERACT_LANGS = process.env.TESSERACT_LANGS || "eng+hin";

function tesseractLangParam() {
  const raw = TESSERACT_LANGS.trim();
  if (!raw) return "eng";
  const parts = raw.split("+").map((s) => s.trim()).filter(Boolean);
  if (parts.length <= 1) return parts[0] || "eng";
  return parts;
}

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 25 * 1024 * 1024 },
});

app.use(cors());
app.use(express.json({ limit: "1mb" }));
app.use(express.static(path.join(__dirname, "..", "public")));

app.get("/api/health", (_req, res) => {
  res.json({
    ok: true,
    service: "step2-multimodal",
    engine: {
      voice: "OpenAI Whisper (local CLI)",
      image: "Tesseract.js",
    },
    whisperModel: process.env.WHISPER_MODEL || "base",
    whisperLanguage: process.env.WHISPER_LANGUAGE || "en",
    tesseractLangs: TESSERACT_LANGS,
    tesseractLangParam: tesseractLangParam(),
  });
});

app.post("/api/input/text", (req, res) => {
  const text = typeof req.body?.text === "string" ? req.body.text.trim() : "";
  if (!text) return res.status(400).json({ error: "Text is required" });
  return res.json({ mode: "text", recognizedText: text });
});

app.post("/api/input/voice", upload.single("audio"), async (req, res) => {
  const tmpRoot = os.tmpdir();
  const id = crypto.randomUUID();
  const workDir = path.join(tmpRoot, `vyapar-whisper-${id}`);
  let ext = ".webm";
  try {
    if (!req.file) return res.status(400).json({ error: "Audio file is required" });

    const mime = req.file.mimetype || "";
    if (mime.includes("wav")) ext = ".wav";
    else if (mime.includes("mpeg") || mime.includes("mp3")) ext = ".mp3";
    else if (mime.includes("mp4") || mime.includes("m4a")) ext = ".m4a";
    else if (mime.includes("ogg")) ext = ".ogg";

    await fs.mkdir(workDir, { recursive: true });
    const inputPath = path.join(workDir, `input${ext}`);
    await fs.writeFile(inputPath, req.file.buffer);

    const recognizedText = await transcribeAudioFile(inputPath, workDir);
    res.json({
      mode: "voice",
      recognizedText,
      whisperModel: process.env.WHISPER_MODEL || "base",
      whisperLanguage: process.env.WHISPER_LANGUAGE || "en",
    });
  } catch (e) {
    console.error(e);
    res.status(500).json({
      error: "Voice to text failed",
      detail: e.message,
      hint:
        "Install: pip install openai-whisper, add ffmpeg to PATH (or rely on bundled ffmpeg for conversion). " +
        "Ensure `whisper` or `python -m whisper` works in a terminal.",
    });
  } finally {
    try {
      await fs.rm(workDir, { recursive: true, force: true });
    } catch (_) {}
  }
});

app.post("/api/input/image", upload.single("image"), async (req, res) => {
  let worker;
  try {
    if (!req.file) return res.status(400).json({ error: "Image file is required" });

    worker = await createWorker(tesseractLangParam());
    const {
      data: { text },
    } = await worker.recognize(req.file.buffer);
    await worker.terminate();
    worker = null;

    res.json({
      mode: "image",
      recognizedText: (text || "").trim(),
      tesseractLangs: TESSERACT_LANGS,
    });
  } catch (e) {
    console.error(e);
    if (worker) {
      try {
        await worker.terminate();
      } catch (_) {}
    }
    res.status(500).json({
      error: "Image to text failed",
      detail: e.message,
    });
  }
});

app.listen(PORT, () => {
  console.log(`Step2 multimodal (Whisper + Tesseract): http://localhost:${PORT}`);
});
