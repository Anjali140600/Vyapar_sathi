const result = document.getElementById("result");

const textForm = document.getElementById("textForm");
const voiceForm = document.getElementById("voiceForm");
const imageForm = document.getElementById("imageForm");

const textInput = document.getElementById("textInput");
const voiceFile = document.getElementById("voiceFile");
const imageFile = document.getElementById("imageFile");

const btnStartRec = document.getElementById("btnStartRec");
const btnStopRec = document.getElementById("btnStopRec");
const recStatus = document.getElementById("recStatus");

let mediaRecorder = null;
let mediaStream = null;
let recordedChunks = [];
let recordedMime = "audio/webm";

function show(data) {
  result.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

async function postJson(url, payload) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const j = await r.json();
  if (!r.ok) throw new Error([j.error, j.detail].filter(Boolean).join(" - "));
  return j;
}

async function postFile(url, fieldName, file, filename) {
  const fd = new FormData();
  if (filename) fd.append(fieldName, file, filename);
  else fd.append(fieldName, file);
  const r = await fetch(url, { method: "POST", body: fd });
  const j = await r.json();
  if (!r.ok) throw new Error([j.error, j.detail].filter(Boolean).join(" - "));
  return j;
}

function pickRecorderMime() {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  for (const t of types) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) return t;
  }
  return "";
}

function blobFilenameForMime(mime) {
  if (mime.includes("mp4")) return "recording.m4a";
  if (mime.includes("webm")) return "recording.webm";
  return "recording.webm";
}

async function startLiveRecording() {
  if (!navigator.mediaDevices?.getUserMedia) {
    show("Microphone not supported in this browser.");
    return;
  }
  const mime = pickRecorderMime();
  mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });
  const opts = mime ? { mimeType: mime, audioBitsPerSecond: 128000 } : { audioBitsPerSecond: 128000 };
  try {
    mediaRecorder = new MediaRecorder(mediaStream, opts);
  } catch {
    mediaRecorder = new MediaRecorder(mediaStream, mime ? { mimeType: mime } : {});
  }
  recordedChunks = [];
  recordedMime = mediaRecorder.mimeType || "audio/webm";
  mediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) recordedChunks.push(e.data);
  };
  mediaRecorder.start(250);
  btnStartRec.disabled = true;
  btnStopRec.disabled = false;
  recStatus.textContent = "Recording… speak now.";
  recStatus.classList.add("rec-on");
}

async function stopLiveRecordingAndSend() {
  if (!mediaRecorder || mediaRecorder.state === "inactive") return;

  const blob = await new Promise((resolve, reject) => {
    mediaRecorder.addEventListener("error", () => reject(new Error("Recorder error")), {
      once: true,
    });
    mediaRecorder.addEventListener(
      "stop",
      () => {
        try {
          const b = new Blob(recordedChunks, { type: recordedMime });
          resolve(b);
        } catch (e) {
          reject(e);
        }
      },
      { once: true }
    );
    if (mediaRecorder.state === "recording") {
      try {
        mediaRecorder.requestData();
      } catch (_) {}
    }
    mediaRecorder.stop();
  });

  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  mediaRecorder = null;
  recordedChunks = [];
  btnStartRec.disabled = false;
  btnStopRec.disabled = true;
  recStatus.textContent = "";
  recStatus.classList.remove("rec-on");

  if (!blob || blob.size < 500) {
    show("Recording too short or empty. Try again and speak a bit longer.");
    return;
  }

  const name = blobFilenameForMime(recordedMime);
  show("Converting voice to text (Whisper)…");
  const out = await postFile("/api/input/voice", "audio", blob, name);
  show(out.recognizedText || "No speech recognized");
}

btnStartRec.addEventListener("click", async () => {
  try {
    await startLiveRecording();
  } catch (err) {
    btnStartRec.disabled = false;
    btnStopRec.disabled = true;
    recStatus.textContent = "";
    recStatus.classList.remove("rec-on");
    show(
      err.name === "NotAllowedError"
        ? "Microphone permission denied. Allow mic for this site and try again."
        : err.message || "Could not start microphone."
    );
  }
});

btnStopRec.addEventListener("click", async () => {
  if (!mediaRecorder || mediaRecorder.state === "inactive") return;
  btnStopRec.disabled = true;
  try {
    await stopLiveRecordingAndSend();
  } catch (err) {
    show(err.message || "Voice processing failed");
  }
});

textForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    show("Processing text...");
    const out = await postJson("/api/input/text", { text: textInput.value });
    show(out.recognizedText || "No text recognized");
  } catch (err) {
    show(err.message || "Text processing failed");
  }
});

voiceForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    if (!voiceFile.files[0]) return show("Please select an audio file first.");
    show("Converting voice to text...");
    const out = await postFile("/api/input/voice", "audio", voiceFile.files[0]);
    show(out.recognizedText || "No speech recognized");
  } catch (err) {
    show(err.message || "Voice processing failed");
  }
});

imageForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    if (!imageFile.files[0]) return show("Please select an image file first.");
    show("Extracting text from image...");
    const out = await postFile("/api/input/image", "image", imageFile.files[0]);
    show(out.recognizedText || "No text found in image");
  } catch (err) {
    show(err.message || "Image processing failed");
  }
});
