import { Database, Loader2, Mic, Pause, Send, Volume2, Waves } from "lucide-react";
import { type MutableRefObject, useEffect, useRef, useState } from "react";
import type { AskResponse } from "../lib/api";

declare global {
  interface Window {
    webkitAudioContext?: typeof AudioContext;
  }
}

type Props = {
  disabled: boolean;
  busy: boolean;
  lastAnswer: AskResponse | null;
  onAskText: (question: string) => void;
  onTranscribeVoice: (audio: Blob) => Promise<string>;
};

type PlaybackState = "idle" | "playing" | "paused";
type PlaybackSource = "audio" | "browser";

export function VoiceConsole({ disabled, busy, lastAnswer, onAskText, onTranscribeVoice }: Props) {
  const [question, setQuestion] = useState("");
  const [recording, setRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [micLevel, setMicLevel] = useState(0);
  const [voiceError, setVoiceError] = useState("");
  const [playbackState, setPlaybackState] = useState<PlaybackState>("idle");
  const [activeWordIndex, setActiveWordIndex] = useState(-1);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const recordingStartedAtRef = useRef<number>(0);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const answerAudioRef = useRef<HTMLAudioElement | null>(null);
  const readAlongTimerRef = useRef<number | null>(null);
  const answerScrollRef = useRef<HTMLDivElement | null>(null);
  const activeWordRef = useRef<HTMLSpanElement | null>(null);
  const playbackSourceRef = useRef<PlaybackSource | null>(null);
  const readTimelineRef = useRef<ReadTimeline | null>(null);

  useEffect(() => {
    if (!recording) return;
    const interval = window.setInterval(() => {
      setRecordingSeconds(Math.floor((Date.now() - recordingStartedAtRef.current) / 1000));
    }, 250);
    return () => window.clearInterval(interval);
  }, [recording]);

  useEffect(() => {
    answerAudioRef.current?.pause();
    answerAudioRef.current = null;
    window.speechSynthesis?.cancel();
    stopReadAlong();
    setPlaybackState("idle");
    setActiveWordIndex(-1);
    playbackSourceRef.current = null;
    readTimelineRef.current = null;
  }, [lastAnswer]);

  useEffect(() => {
    if (playbackState !== "playing" || activeWordIndex < 0 || !answerScrollRef.current || !activeWordRef.current) return;
    const container = answerScrollRef.current;
    const word = activeWordRef.current;
    const containerRect = container.getBoundingClientRect();
    const wordRect = word.getBoundingClientRect();
    const upperBand = containerRect.top + container.clientHeight * 0.24;
    const lowerBand = containerRect.top + container.clientHeight * 0.62;
    if (wordRect.top >= upperBand && wordRect.bottom <= lowerBand) return;

    const targetTop = container.scrollTop + (wordRect.top - (containerRect.top + container.clientHeight * 0.42));
    container.scrollTo({ top: Math.max(0, targetTop), behavior: "auto" });
  }, [activeWordIndex, playbackState]);

  async function toggleRecording() {
    if (recording) {
      if (Date.now() - recordingStartedAtRef.current < 900) {
        setVoiceError("Record for at least one second before sending.");
        return;
      }
      recorderRef.current?.stop();
      setRecording(false);
      stopMicLevelMonitor();
      return;
    }

    try {
      setVoiceError("");
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });
      const mimeType = preferredMimeType();
      startMicLevelMonitor(stream);
      const recorder = new MediaRecorder(stream, {
        ...(mimeType ? { mimeType } : {}),
        audioBitsPerSecond: 128000,
      });
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const type = recorder.mimeType || mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type });
        stopMicLevelMonitor();
        stream.getTracks().forEach((track) => track.stop());
        if (blob.size < 800) {
          setVoiceError("The recording was too short or silent. Try again closer to the mic.");
          return;
        }
        onTranscribeVoice(blob).then((transcript) => {
          if (!transcript) return;
          setQuestion(transcript);
          setVoiceError("Transcript ready. Review it, then press send.");
        });
      };
      recorder.start(250);
      recorderRef.current = recorder;
      recordingStartedAtRef.current = Date.now();
      setRecordingSeconds(0);
      setRecording(true);
    } catch {
      setVoiceError("Microphone permission is blocked. Allow microphone access in the browser.");
      stopMicLevelMonitor();
    }
  }

  function submit() {
    const trimmed = question.trim();
    if (!trimmed) return;
    onAskText(trimmed);
    setQuestion("");
  }

  function togglePlayback() {
    if (!lastAnswer) return;
    if (playbackState === "playing") {
      pausePlayback();
      return;
    }
    if (playbackState === "paused") {
      resumePlayback();
      return;
    }
    startPlayback();
  }

  function startPlayback() {
    if (!lastAnswer) return;
    answerAudioRef.current?.pause();
    window.speechSynthesis?.cancel();
    stopReadAlong();
    setActiveWordIndex(-1);

    if (!lastAnswer.audio_base64 || !lastAnswer.audio_mime_type) {
      playBrowserSpeech(lastAnswer.answer);
      return;
    }

    const audio = new Audio(`data:${lastAnswer.audio_mime_type};base64,${lastAnswer.audio_base64}`);
    const spokenText = cleanVisibleAnswer(lastAnswer.answer);
    const timeline = createReadTimeline(spokenText);
    readTimelineRef.current = timeline;
    playbackSourceRef.current = "audio";
    audio.ontimeupdate = () => {
      if (!audio.duration || !Number.isFinite(audio.duration) || timeline.wordCount === 0) return;
      setActiveWordIndex(wordIndexForProgress(timeline, audio.currentTime / audio.duration));
    };
    audio.onplay = () => setPlaybackState("playing");
    audio.onended = () => {
      stopReadAlong();
      setPlaybackState("idle");
      setActiveWordIndex(-1);
      playbackSourceRef.current = null;
    };
    audio.onpause = () => {
      stopReadAlong();
      if (audio.ended) return;
      setPlaybackState("paused");
    };
    answerAudioRef.current = audio;
    audio.play().catch(() => playBrowserSpeech(spokenText));
  }

  function pausePlayback() {
    if (playbackSourceRef.current === "audio") {
      answerAudioRef.current?.pause();
      return;
    }
    if (playbackSourceRef.current === "browser") {
      window.speechSynthesis?.pause();
      stopReadAlong();
      setPlaybackState("paused");
    }
  }

  function resumePlayback() {
    if (playbackSourceRef.current === "audio") {
      answerAudioRef.current?.play();
      return;
    }
    if (playbackSourceRef.current === "browser") {
      window.speechSynthesis?.resume();
      const timeline = readTimelineRef.current;
      if (timeline) startEstimatedReadAlong(timeline, activeWordIndex);
      setPlaybackState("playing");
    }
  }

  function playBrowserSpeech(answer: string) {
    const spokenText = cleanVisibleAnswer(answer);
    const timeline = createReadTimeline(spokenText);
    if (!spokenText || !window.speechSynthesis) return;
    playbackSourceRef.current = "browser";
    readTimelineRef.current = timeline;

    const utterance = new SpeechSynthesisUtterance(spokenText);
    utterance.rate = 0.96;
    utterance.onstart = () => {
      setPlaybackState("playing");
      startEstimatedReadAlong(timeline);
    };
    utterance.onboundary = (event) => {
      if (event.name !== "word" || typeof event.charIndex !== "number") return;
      setActiveWordIndex(wordIndexAtChar(spokenText, event.charIndex));
    };
    utterance.onend = () => {
      stopReadAlong();
      setPlaybackState("idle");
      setActiveWordIndex(-1);
      playbackSourceRef.current = null;
    };
    utterance.onerror = () => {
      stopReadAlong();
      setPlaybackState("idle");
      setActiveWordIndex(-1);
      playbackSourceRef.current = null;
    };
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }

  function startEstimatedReadAlong(timeline: ReadTimeline, startWordIndex = -1) {
    stopReadAlong();
    if (timeline.wordCount === 0) return;
    const startProgress = startWordIndex >= 0 ? progressForWordIndex(timeline, startWordIndex) : 0;
    const estimatedMs = Math.max(1000, timeline.totalWeight * 230 * (1 - startProgress));
    const startedAt = Date.now();
    readAlongTimerRef.current = window.setInterval(() => {
      const elapsedProgress = Math.min(1, (Date.now() - startedAt) / estimatedMs);
      const progress = startProgress + (1 - startProgress) * elapsedProgress;
      setActiveWordIndex(wordIndexForProgress(timeline, progress));
    }, 180);
  }

  function stopReadAlong() {
    if (readAlongTimerRef.current !== null) {
      window.clearInterval(readAlongTimerRef.current);
      readAlongTimerRef.current = null;
    }
  }

  function startMicLevelMonitor(stream: MediaStream) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;

    const audioContext = new AudioContextClass();
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.72;
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);
    audioContextRef.current = audioContext;
    analyserRef.current = analyser;

    const samples = new Uint8Array(analyser.frequencyBinCount);
    const tick = () => {
      analyser.getByteTimeDomainData(samples);
      let sum = 0;
      for (const sample of samples) {
        const centered = sample - 128;
        sum += centered * centered;
      }
      const rms = Math.sqrt(sum / samples.length);
      setMicLevel(Math.min(100, Math.round((rms / 42) * 100)));
      animationFrameRef.current = window.requestAnimationFrame(tick);
    };
    tick();
  }

  function stopMicLevelMonitor() {
    if (animationFrameRef.current !== null) {
      window.cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    analyserRef.current = null;
    audioContextRef.current?.close();
    audioContextRef.current = null;
    setMicLevel(0);
  }

  return (
    <section className="console">
      <div className="console-top">
        <div>
          <span className="eyebrow">Live assistant</span>
          <h1>Ask the book by voice</h1>
        </div>
        <button className={recording ? "icon-button danger" : "icon-button"} disabled={disabled || busy} onClick={toggleRecording} title="Record question">
          {recording ? <Pause aria-hidden="true" /> : <Mic aria-hidden="true" />}
        </button>
      </div>

      <div className={recording ? "recording-status active" : "recording-status"}>
        {recording ? `Recording ${recordingSeconds}s` : voiceError || "Use Chrome for the most reliable microphone capture."}
      </div>

      {recording ? (
        <div className="mic-meter" aria-label={`Microphone input level ${micLevel}%`}>
          <span style={{ width: `${micLevel}%` }} />
        </div>
      ) : null}

      <div className="question-bar">
        <input
          disabled={disabled || busy}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") submit();
          }}
          placeholder={disabled ? "Upload or select a document first" : "Type a question or use the microphone"}
          value={question}
        />
        <button disabled={disabled || busy || !question.trim()} onClick={submit} title="Send question">
          <Send aria-hidden="true" />
        </button>
      </div>

      <div className="answer-surface">
        {busy ? (
          <div className="generation-state">
            <Loader2 className="spin" aria-hidden="true" />
            <div>
              <span className="starter-kicker">Generating answer</span>
              <h2>Searching the PDF and preparing speech</h2>
              <p>Retrieving evidence, drafting a grounded response, and creating browser playback.</p>
            </div>
          </div>
        ) : lastAnswer ? (
          <>
            <div className="answer-scroll" ref={answerScrollRef}>
              <div className="transcript">
                <span>Recognized question</span>
                <p>{lastAnswer.question}</p>
              </div>
              <FormattedAnswer
                activeWordIndex={playbackState !== "idle" ? activeWordIndex : -1}
                activeWordRef={activeWordRef}
                answer={lastAnswer.answer}
              />
            </div>
            <button className="secondary-action sticky-playback" onClick={togglePlayback}>
              {playbackState === "playing" ? <Pause aria-hidden="true" /> : <Volume2 aria-hidden="true" />}
              {playbackState === "playing" ? "Pause playback" : playbackState === "paused" ? "Resume playback" : "Listen to answer"}
            </button>
          </>
        ) : (
          <div className="starter-state">
            <div className="starter-copy">
              <span className="starter-kicker">Ready when you are</span>
              <h2>Ask your PDF by voice or text</h2>
              <p>Transcribe your question, retrieve grounded evidence, then hear the answer in the browser.</p>
            </div>
            <div className="pipeline-cards">
              <div className="pipeline-card">
                <span className="pipeline-index">01</span>
                <Waves aria-hidden="true" />
                <strong>Speech recognition</strong>
                <p>Speech to editable text.</p>
              </div>
              <div className="pipeline-card">
                <span className="pipeline-index">02</span>
                <Database aria-hidden="true" />
                <strong>Evidence retrieval</strong>
                <p>Evidence-backed answers.</p>
              </div>
              <div className="pipeline-card">
                <span className="pipeline-index">03</span>
                <Volume2 aria-hidden="true" />
                <strong>Voice playback</strong>
                <p>Spoken playback.</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function preferredMimeType() {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
  ];
  return types.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function FormattedAnswer({
  answer,
  activeWordIndex,
  activeWordRef,
}: {
  answer: string;
  activeWordIndex: number;
  activeWordRef: MutableRefObject<HTMLSpanElement | null>;
}) {
  const blocks = formatAnswerBlocks(answer);
  let nextWordIndex = 0;

  return (
    <div className="answer">
      {blocks.map((block, index) => (
        block.kind === "list" ? (
          <ul key={index}>
            {block.items.map((item, itemIndex) => (
              <li key={itemIndex}>{renderAnswerText(item, activeWordIndex, activeWordRef, () => nextWordIndex++)}</li>
            ))}
          </ul>
        ) : (
          <p key={index}>{renderAnswerText(block.text, activeWordIndex, activeWordRef, () => nextWordIndex++)}</p>
        )
      ))}
    </div>
  );
}

type AnswerBlock = { kind: "paragraph"; text: string } | { kind: "list"; items: string[] };

function formatAnswerBlocks(answer: string): AnswerBlock[] {
  const cleaned = cleanAnswerForDisplay(answer);

  const lines = cleaned
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

  const blocks: AnswerBlock[] = [];
  let listItems: string[] = [];

  function flushList() {
    if (listItems.length > 0) {
      blocks.push({ kind: "list", items: listItems });
      listItems = [];
    }
  }

  for (const line of lines) {
    const bullet = line.match(/^(?:[-*]|[0-9]+[.)])\s+(.+)$/);
    if (bullet) {
      listItems.push(bullet[1].trim());
      continue;
    }

    flushList();
    blocks.push({ kind: "paragraph", text: line });
  }

  flushList();
  return blocks.length > 0 ? blocks : [{ kind: "paragraph", text: cleaned.trim() }];
}

function cleanVisibleAnswer(answer: string) {
  return baseCleanAnswer(answer)
    .replace(/\s+\*\s+/g, ". ")
    .replace(/(?:^|\n)\s*(?:[-*]|[0-9]+[.)])\s+/g, " ")
    .replace(/\*/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function cleanAnswerForDisplay(answer: string) {
  return baseCleanAnswer(answer)
    .replace(/\s+\*\s+/g, "\n* ")
    .replace(/^\*\s*/g, "* ")
    .trim();
}

function baseCleanAnswer(answer: string) {
  return answer
    .replace(/\s*\[Source[^\]]*\]/g, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/\*([^*\n]+)\*/g, "$1")
    .replace(/_([^_\n]+)_/g, "$1");
}

type ReadTimeline = {
  checkpoints: number[];
  totalWeight: number;
  wordCount: number;
};

function createReadTimeline(text: string): ReadTimeline {
  const words = text.match(/\S+/g) ?? [];
  const checkpoints: number[] = [];
  let totalWeight = 0;

  for (const word of words) {
    totalWeight += wordWeight(word);
    checkpoints.push(totalWeight);
  }

  return { checkpoints, totalWeight, wordCount: words.length };
}

function wordIndexForProgress(timeline: ReadTimeline, progress: number) {
  if (timeline.wordCount === 0 || timeline.totalWeight <= 0) return -1;
  const target = Math.max(0, Math.min(1, progress)) * timeline.totalWeight;
  const index = timeline.checkpoints.findIndex((checkpoint) => checkpoint >= target);
  return index === -1 ? timeline.wordCount - 1 : index;
}

function progressForWordIndex(timeline: ReadTimeline, wordIndex: number) {
  if (timeline.wordCount === 0 || timeline.totalWeight <= 0) return 0;
  const safeIndex = Math.max(0, Math.min(timeline.wordCount - 1, wordIndex));
  return timeline.checkpoints[safeIndex] / timeline.totalWeight;
}

function wordWeight(word: string) {
  const normalized = word.replace(/[^\p{L}\p{N}]/gu, "");
  let weight = 1 + Math.max(0, normalized.length - 6) * 0.035;
  if (/[,:;]$/.test(word)) weight += 0.45;
  if (/[.!?]$/.test(word)) weight += 0.9;
  if (/[)]$/.test(word)) weight += 0.25;
  return weight;
}

function wordIndexAtChar(text: string, charIndex: number) {
  const before = text.slice(0, Math.max(0, charIndex)).trim();
  if (!before) return 0;
  return Math.max(0, before.split(/\s+/).length - 1);
}

function renderAnswerText(
  text: string,
  activeWordIndex: number,
  activeWordRef: MutableRefObject<HTMLSpanElement | null>,
  nextIndex: () => number,
) {
  return text.split(/(\s+)/).map((part, index) => {
    if (/^\s+$/.test(part)) return part;
    const wordIndex = nextIndex();
    const isRead = activeWordIndex >= 0 && wordIndex <= activeWordIndex;
    const isCurrent = activeWordIndex === wordIndex;
    return (
      <span
        className={isRead ? "read-word active" : "read-word"}
        key={`${wordIndex}-${index}`}
        ref={isCurrent ? activeWordRef : undefined}
      >
        {part}
      </span>
    );
  });
}
