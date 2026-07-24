const fs = require("fs/promises");
const fsSync = require("fs");
const path = require("path");
const { execFile } = require("child_process");
const { promisify } = require("util");
const ffmpegPath = require("ffmpeg-static");

const execFileAsync = promisify(execFile);

/** Whisper calls `ffmpeg` from PATH; prepend bundled ffmpeg-static so no system install is required. */
function childEnvWithFfmpeg() {
  const env = { ...process.env };
  if (ffmpegPath) {
    const dir = path.dirname(ffmpegPath);
    env.PATH = `${dir}${path.delimiter}${env.PATH || ""}`;
  }
  return env;
}

/**
 * Conda/venv `Scripts` is often missing from PATH when Node is started from an IDE — ENOENT for whisper/python/py.
 * Prepend conda base + venv Scripts (same idea as `conda activate`).
 */
function prependCondaAndVenvToPath(env) {
  const sep = path.delimiter;
  const front = [];
  const add = (p) => {
    if (p && !front.includes(p)) front.push(p);
  };
  const conda = process.env.CONDA_PREFIX;
  if (conda) {
    add(path.join(conda, "Scripts"));
    add(path.join(conda, "Library", "bin"));
    add(path.join(conda, "bin"));
  }
  if (process.env.VIRTUAL_ENV) {
    add(path.join(process.env.VIRTUAL_ENV, "Scripts"));
  }
  if (front.length === 0) return env;
  return {
    ...env,
    PATH: `${front.join(sep)}${sep}${env.PATH || ""}`,
  };
}

/**
 * Avoid mixing Anaconda with a separate Python "user site" (e.g. `%APPDATA%\Python\Python313`).
 * That mix often causes: ModuleNotFoundError: No module named 'numpy._utils'
 */
function childEnvForWhisperCli() {
  let env = childEnvWithFfmpeg();
  env = prependCondaAndVenvToPath(env);
  env.PYTHONNOUSERSITE = "1";
  return env;
}

function whisperExecOpts() {
  return {
    env: childEnvForWhisperCli(),
    maxBuffer: 50 * 1024 * 1024,
    windowsHide: true,
    /**
     * Must stay false on Windows: with shell:true, cmd.exe splits `--initial_prompt English speech...`
     * into multiple argv tokens → "unrecognized arguments: speech, Indian names."
     * PATH already includes CONDA_PREFIX\Scripts (whisper.exe resolves via execFile).
     */
    shell: false,
  };
}

/**
 * Converts audio to 16 kHz mono WAV using bundled ffmpeg.
 */
async function convertToWav(inputPath, wavPath) {
  if (!ffmpegPath) {
    throw new Error("ffmpeg-static path missing");
  }
  await execFileAsync(
    ffmpegPath,
    ["-y", "-i", inputPath, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wavPath],
    { env: childEnvWithFfmpeg(), windowsHide: true }
  );
}

function whisperLanguageAndPrompt() {
  const raw = (process.env.WHISPER_LANGUAGE ?? "en").trim();
  if (!raw || raw.toLowerCase() === "auto") return { language: null, initialPrompt: null };
  const prompt = process.env.WHISPER_INITIAL_PROMPT?.trim();
  return { language: raw, initialPrompt: prompt || null };
}

function whisperArgs(wavPath, outDir, model, fp16) {
  const base = [wavPath, "--model", model, "--output_dir", outDir, "--output_format", "txt"];
  if (fp16 === false) base.push("--fp16", "False");
  const modelDir = process.env.WHISPER_MODEL_DIR?.trim();
  if (modelDir) {
    base.push("--model_dir", modelDir);
  }
  const { language, initialPrompt } = whisperLanguageAndPrompt();
  if (language) {
    base.push("--language", language);
  }
  if (initialPrompt) {
    base.push("--initial_prompt", initialPrompt);
  }
  return base;
}

function buildWhisperTryRuns(wavPath, outDir, model, fp16) {
  const args = whisperArgs(wavPath, outDir, model, fp16);
  const modWhisper = ["-m", "whisper", ...args];
  const win = process.platform === "win32";

  const condaWhisperExe =
    win && process.env.CONDA_PREFIX
      ? path.join(process.env.CONDA_PREFIX, "Scripts", "whisper.exe")
      : null;

  const runs = [];
  if (condaWhisperExe && fsSync.existsSync(condaWhisperExe)) {
    runs.push({ cmd: condaWhisperExe, args });
  }
  runs.push({ cmd: "whisper", args });

  const pyExe = process.env.WHISPER_PYTHON?.trim();
  if (pyExe) {
    runs.unshift({ cmd: pyExe, args: modWhisper });
  }

  const condaPy =
    process.env.CONDA_PREFIX && path.join(process.env.CONDA_PREFIX, "python.exe");
  if (win && condaPy && fsSync.existsSync(condaPy)) {
    runs.push({ cmd: condaPy, args: modWhisper });
  }

  if (win) {
    runs.push(
      { cmd: "py", args: modWhisper },
      { cmd: "python", args: modWhisper }
    );
  } else {
    runs.push(
      { cmd: "python3", args: modWhisper },
      { cmd: "python", args: modWhisper },
      { cmd: "py", args: modWhisper }
    );
  }
  return runs;
}

function isDiskFullError(message) {
  return /No space left on device|Errno\s*28/i.test(message || "");
}

/**
 * Runs OpenAI Whisper CLI (pip install openai-whisper). Tries WHISPER_CMD / WHISPER_PYTHON, then whisper, then py/python.
 */
async function transcribeWithWhisper(wavPath, outDir) {
  /** Default `base` (~140MB) instead of `small` (~460MB) to reduce disk use. */
  const model = process.env.WHISPER_MODEL || "base";
  const fp16Env = process.env.WHISPER_FP16;
  const fp16 =
    fp16Env === undefined || fp16Env === ""
      ? false
      : fp16Env !== "0" && fp16Env !== "false";

  const custom = process.env.WHISPER_CMD?.trim();
  if (custom) {
    await execFileAsync(custom, whisperArgs(wavPath, outDir, model, fp16), whisperExecOpts());
    return;
  }

  const tryRuns = buildWhisperTryRuns(wavPath, outDir, model, fp16);

  const errors = [];
  for (const run of tryRuns) {
    try {
      await execFileAsync(run.cmd, run.args, whisperExecOpts());
      return;
    } catch (e) {
      const msg = e.message || String(e);
      if (isDiskFullError(msg)) {
        throw new Error(
          `Whisper could not download or save the model (disk full — Errno 28). ` +
            `Free at least ~500MB on the drive used for the model cache, or use a smaller model and optional cache folder:\n` +
            `- Set WHISPER_MODEL=tiny (~75MB) or base (~140MB) in .env (avoid small/medium/large until you have space).\n` +
            `- Set WHISPER_MODEL_DIR=D:\\some\\folder\\with\\free\\space so the download uses another drive.\n` +
            `Original error: ${msg.slice(0, 800)}`
        );
      }
      errors.push(`${run.cmd}: ${msg}`);
    }
  }
  const hint =
    process.platform === "win32"
      ? " On Windows set WHISPER_CMD to full path to whisper.exe (e.g. under Anaconda Scripts), or WHISPER_PYTHON to python.exe."
      : "";
  throw new Error(`Whisper failed (${tryRuns.length} attempts).${hint}\n${errors.join("\n")}`);
}

/**
 * @param {string} inputPath - path to uploaded audio
 * @param {string} tmpDir - temp directory for wav + output
 * @returns {Promise<string>} transcript text
 */
async function transcribeAudioFile(inputPath, tmpDir) {
  const base = path.basename(inputPath, path.extname(inputPath));
  const wavPath = path.join(tmpDir, `${base}.wav`);
  await convertToWav(inputPath, wavPath);

  await transcribeWithWhisper(wavPath, tmpDir);

  const txtPath = path.join(tmpDir, `${base}.txt`);
  const text = await fs.readFile(txtPath, "utf8");
  return text.trim();
}

module.exports = { transcribeAudioFile, convertToWav };
