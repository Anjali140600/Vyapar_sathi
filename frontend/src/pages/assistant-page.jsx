import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bot,
  FileUp,
  ImageIcon,
  LoaderCircle,
  Mic,
  MicOff,
  Plus,
  SendHorizonal,
  Trash2,
  Radio,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { chatApi, multimodalApi } from "@/lib/api";

const suggestedPrompts = [
  "What is my total sales this month?",
  "How much GST did I collect?",
  "Show top expense categories",
  "What is my rent amount?",
];

// ── MediaRecorder helpers (ported from step2 app.js) ─────────────────────────

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

// ── Live Mic Hook ─────────────────────────────────────────────────────────────

function useLiveMic({ onTranscript, onError }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const chunksRef = useRef([]);
  const mimeRef = useRef("audio/webm");

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      onError("Microphone not supported in this browser.");
      return;
    }
    const mime = pickRecorderMime();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      mediaStreamRef.current = stream;
      const opts = mime
        ? { mimeType: mime, audioBitsPerSecond: 128000 }
        : { audioBitsPerSecond: 128000 };
      let recorder;
      try {
        recorder = new MediaRecorder(stream, opts);
      } catch {
        recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : {});
      }
      chunksRef.current = [];
      mimeRef.current = recorder.mimeType || "audio/webm";
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.start(250);
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (err) {
      onError(
        err.name === "NotAllowedError"
          ? "Microphone permission denied. Allow mic access and try again."
          : err.message || "Could not start microphone."
      );
    }
  }, [onError]);

  const stop = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") return;

    setIsSending(true);
    const blob = await new Promise((resolve, reject) => {
      recorder.addEventListener("error", () => reject(new Error("Recorder error")), { once: true });
      recorder.addEventListener(
        "stop",
        () => {
          try {
            resolve(new Blob(chunksRef.current, { type: mimeRef.current }));
          } catch (e) {
            reject(e);
          }
        },
        { once: true }
      );
      try { recorder.requestData(); } catch (_) {}
      recorder.stop();
    });

    // Clean up stream
    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    mediaStreamRef.current = null;
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    setIsRecording(false);

    if (!blob || blob.size < 500) {
      setIsSending(false);
      onError("Recording too short. Speak a bit longer and try again.");
      return;
    }

    try {
      const filename = blobFilenameForMime(mimeRef.current);
      const res = await multimodalApi.inputVoice(blob, filename);
      onTranscript(res.data.recognizedText || "");
    } catch (err) {
      onError(err.response?.data?.detail || err.message || "Voice processing failed.");
    } finally {
      setIsSending(false);
    }
  }, [onTranscript, onError]);

  return { isRecording, isSending, start, stop };
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function AssistantPage() {
  const queryClient = useQueryClient();
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [draft, setDraft] = useState("");
  const messagesEndRef = useRef(null);

  const sessionsQuery = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: () => chatApi.sessions().then((res) => res.data.data || []),
  });

  const historyQuery = useQuery({
    queryKey: ["chat-history", currentSessionId],
    queryFn: () => chatApi.history(currentSessionId).then((res) => res.data.data || []),
    enabled: Boolean(currentSessionId),
  });

  const messages = useMemo(() => historyQuery.data || [], [historyQuery.data]);

  const sendMutation = useMutation({
    mutationFn: (payload) => chatApi.send(payload).then((res) => res.data.data),
    onSuccess: (data) => {
      setCurrentSessionId(data.sessionId);
      setDraft("");
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      queryClient.invalidateQueries({ queryKey: ["chat-history", data.sessionId] });
    },
    onError: (error) => toast.error(error.response?.data?.detail || "Message could not be sent."),
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentSessionId, sendMutation.isPending]);

  // ── upload-then-process (for bill upload button) ───────────────────────
  const uploadMutation = useMutation({
    mutationFn: async ({ file, kind }) => {
      const upload = await multimodalApi.upload(file, currentSessionId || "");
      if (kind === "bill") {
        const result = await multimodalApi.ocr(upload.data.id);
        return { kind, result: result.data };
      }
      const result = await multimodalApi.stt(upload.data.id);
      return { kind, result: result.data };
    },
    onSuccess: ({ kind, result }) => {
      if (kind === "voice") {
        setDraft(result.transcript || "");
        toast.success("Voice note transcribed. Review and send it.");
      } else {
        toast.success("Bill processed. OCR result added to the conversation.");
        sendMutation.mutate({
          message: `Bill OCR result: ${result.text || "Processed bill"} Amount ${result.extracted_data?.amount || ""}`,
          sessionId: currentSessionId,
        });
      }
    },
    onError: () => toast.error("File could not be processed."),
  });



  // ── live mic (step-2 style) ────────────────────────────────────────────
  const { isRecording, isSending: isMicSending, start: startMic, stop: stopMic } = useLiveMic({
    onTranscript: (text) => {
      setDraft(text);
      toast.success("Voice transcribed — review and send.");
    },
    onError: (msg) => toast.error(msg),
  });

  const handleSend = () => {
    const message = draft.trim();
    if (!message) return;
    sendMutation.mutate({ message, sessionId: currentSessionId });
  };

  const isInputBusy = sendMutation.isPending || uploadMutation.isPending || isMicSending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Finance Assistant"
        description="Chat with your business data, GST knowledge base, or multimodal uploads."
      />

      <div className="grid gap-4 xl:grid-cols-[280px_1fr_280px]">
        {/* ── Sessions sidebar ─────────────────────────────────────────── */}
        <Card className="h-[calc(100vh-12rem)] overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
            <div>
              <p className="font-display font-bold">Sessions</p>
              <p className="text-xs text-slate-500">Recent chats</p>
            </div>
            <Button size="icon" variant="ghost" onClick={() => setCurrentSessionId(null)}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          <div className="space-y-2 overflow-y-auto p-3">
            {(sessionsQuery.data || []).map((session) => (
              <button
                key={session.id}
                type="button"
                onClick={() => setCurrentSessionId(session.id)}
                className={`w-full rounded-2xl border p-3 text-left ${
                  currentSessionId === session.id
                    ? "border-assistant bg-assistant/10"
                    : "border-slate-200 dark:border-slate-800"
                }`}
              >
                <p className="truncate font-medium">{session.title}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {new Date(session.date).toLocaleDateString("en-IN")}
                </p>
              </button>
            ))}
          </div>
        </Card>

        {/* ── Chat panel ───────────────────────────────────────────────── */}
        <Card className="flex h-[calc(100vh-12rem)] flex-col overflow-hidden">
          <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-display text-lg font-bold">Vyapar Sathi Assistant</p>
                <p className="text-sm text-slate-500">
                  Ask about sales, GST, expenses — or upload a bill / speak.
                </p>
              </div>
              <Badge variant="assistant">Live assistant</Badge>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
            {!currentSessionId && !sendMutation.isPending ? (
              <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">
                Start a new conversation using a prompt chip below, type a question, or speak.
              </div>
            ) : null}

            {messages.map((message, index) => (
              <MessageBubble key={`${message.role}-${index}`} message={message} />
            ))}

            <AnimatePresence>
              {sendMutation.isPending ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex gap-3"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-assistant/15 text-assistant">
                    <Bot className="h-5 w-5" />
                  </div>
                  <div className="rounded-2xl bg-slate-100 px-4 py-3 dark:bg-slate-800">
                    <div className="flex gap-1">
                      <span className="h-2 w-2 animate-bounce rounded-full bg-assistant [animation-delay:-0.3s]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-assistant [animation-delay:-0.15s]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-assistant" />
                    </div>
                  </div>
                </motion.div>
              ) : null}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="border-t border-slate-200 px-5 py-4 dark:border-slate-800">
            {/* Suggested prompts chips */}
            <div className="mb-3 flex flex-wrap gap-2">
              {suggestedPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setDraft(prompt)}
                  className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                >
                  {prompt}
                </button>
              ))}
            </div>

            {/* Multimodal toolbar */}
            <div className="mb-3 flex flex-wrap items-center gap-2">
              {/* Upload Bill */}
              <UploadButton
                label="Upload Bill"
                icon={FileUp}
                accept="image/*"
                disabled={isInputBusy}
                onChange={(file) => uploadMutation.mutate({ file, kind: "bill" })}
              />

              {/* Upload Voice file */}
              <UploadButton
                label="Upload Voice"
                icon={Mic}
                accept="audio/*"
                disabled={isInputBusy}
                onChange={(file) => uploadMutation.mutate({ file, kind: "voice" })}
              />



              {/* Live mic recording (step-2 feature) */}
              <LiveMicButton
                isRecording={isRecording}
                isSending={isMicSending}
                disabled={isInputBusy && !isRecording}
                onStart={startMic}
                onStop={stopMic}
              />
            </div>

            {/* Mic status indicator */}
            <AnimatePresence>
              {isRecording && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mb-2 flex items-center gap-2 text-sm text-red-500"
                >
                  <Radio className="h-4 w-4 animate-pulse" />
                  <span>Recording… speak now, then click Stop &amp; Transcribe.</span>
                </motion.div>
              )}
              {isMicSending && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mb-2 flex items-center gap-2 text-sm text-slate-500"
                >
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                  <span>Converting voice to text (Whisper)…</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Text input + send */}
            <div className="flex gap-3">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Ask about sales, GST, rent, or upload a bill…"
                className="min-h-14 flex-1 rounded-2xl border border-slate-200 bg-white/70 px-4 py-3 text-sm outline-none focus:border-assistant dark:border-slate-700 dark:bg-slate-950/50"
              />
              <Button
                className="h-auto px-4"
                onClick={handleSend}
                disabled={isInputBusy}
              >
                {sendMutation.isPending ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <SendHorizonal className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </Card>

        {/* ── Right panel ──────────────────────────────────────────────── */}
        <Card className="h-[calc(100vh-12rem)] overflow-hidden">
          <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-800">
            <p className="font-display font-bold">Suggested Prompts</p>
            <p className="text-xs text-slate-500">Business-ready starter questions</p>
          </div>
          <div className="space-y-3 p-4">
            {suggestedPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => setDraft(prompt)}
                className="w-full rounded-2xl border border-slate-200 p-3 text-left text-sm hover:border-assistant hover:bg-assistant/5 dark:border-slate-800"
              >
                {prompt}
              </button>
            ))}
            <Button
              variant="outline"
              className="w-full"
              onClick={async () => {
                if (!currentSessionId) return toast.info("Open a saved session first.");
                try {
                  await chatApi.delete(currentSessionId);
                  toast.success("Chat deleted.");
                  setCurrentSessionId(null);
                  queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
                } catch {
                  toast.error("Could not delete that chat.");
                }
              }}
            >
              <Trash2 className="h-4 w-4" />
              Delete Current Chat
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

/** Generic file upload button */
function UploadButton({ label, icon: Icon, accept, disabled, onChange }) {
  return (
    <label
      className={`inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium transition-colors hover:border-assistant hover:bg-assistant/5 dark:border-slate-700 ${
        disabled ? "pointer-events-none opacity-50" : ""
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
      <input
        type="file"
        hidden
        accept={accept}
        disabled={disabled}
        onChange={(e) => e.target.files?.[0] && onChange(e.target.files[0])}
      />
    </label>
  );
}

/** Live microphone record / stop button (step-2 feature) */
function LiveMicButton({ isRecording, isSending, disabled, onStart, onStop }) {
  if (isSending) {
    return (
      <span className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium opacity-70 dark:border-slate-700">
        <LoaderCircle className="h-4 w-4 animate-spin text-assistant" />
        Transcribing…
      </span>
    );
  }

  if (isRecording) {
    return (
      <button
        id="btnStopRec"
        type="button"
        onClick={onStop}
        className="inline-flex items-center gap-2 rounded-xl border border-red-400 bg-red-50 px-3 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-100 dark:border-red-700 dark:bg-red-900/20 dark:text-red-400"
      >
        <MicOff className="h-4 w-4 animate-pulse" />
        Stop &amp; Transcribe
      </button>
    );
  }

  return (
    <button
      id="btnStartRec"
      type="button"
      disabled={disabled}
      onClick={onStart}
      className={`inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium transition-colors hover:border-assistant hover:bg-assistant/5 dark:border-slate-700 ${
        disabled ? "pointer-events-none opacity-50" : ""
      }`}
    >
      <Mic className="h-4 w-4" />
      Start Recording
    </button>
  );
}

function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const type = classifyAnswer(message.content);

  if (!isUser && type === "gst") {
    return (
      <div className="max-w-[85%] rounded-2xl border border-assistant/20 bg-assistant/10 p-4 text-sm text-slate-700 dark:text-slate-100">
        {message.content}
      </div>
    );
  }

  if (!isUser && type === "data") {
    return (
      <div className="max-w-[85%] rounded-2xl border border-slate-200 bg-white/80 p-4 text-sm dark:border-slate-800 dark:bg-slate-950/50">
        <p className="font-semibold text-slate-900 dark:text-slate-100">Data insight</p>
        <p className="mt-2 text-slate-600 dark:text-slate-300">{message.content}</p>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
          isUser ? "bg-slateDeep text-white" : "bg-slate-100 dark:bg-slate-800"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}

function classifyAnswer(text = "") {
  const lower = text.toLowerCase();
  if (/(gst|cgst|sgst|igst|tax|law|rule)/.test(lower)) return "gst";
  if (/(mysql|sales|expenses|profit|amount|transaction)/.test(lower)) return "data";
  return "mixed";
}
