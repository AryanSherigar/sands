/**
 * Capture-side counterpart to ambient-soundtrack.ts's playback engine.
 * Unlike that file's app-wide singleton, a MicRecorder is per-gesture and
 * short-lived — instantiate one per recording, not once globally.
 */

export type MicRecorderErrorReason =
  | "permission-denied"
  | "no-device"
  | "unsupported-browser"
  | "recorder-error";

export class MicRecorderError extends Error {
  constructor(
    public reason: MicRecorderErrorReason,
    message: string,
  ) {
    super(message);
  }
}

const CANDIDATE_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/mp4",
];

const SPEECH_AUDIO_CONSTRAINTS: MediaTrackConstraints = {
  channelCount: 1,
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
};

/** The first browser-supported MediaRecorder MIME type, or null if none is
 * available. The backend's Speech-to-Text V2 integration uses auto-detect
 * decoding, so this isn't filtered to a fixed codec allowlist — any type
 * MediaRecorder can actually produce is passed through as-is. */
function getSupportedMimeType(): string | null {
  if (typeof MediaRecorder === "undefined") return null;
  return CANDIDATE_MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type)) ?? null;
}

export function isVoiceInputSupported(): boolean {
  return (
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    getSupportedMimeType() !== null
  );
}

function toMicRecorderError(err: unknown): MicRecorderError {
  const name = err instanceof DOMException ? err.name : "";
  if (name === "NotAllowedError" || name === "SecurityError") {
    return new MicRecorderError("permission-denied", "Microphone access was denied.");
  }
  return new MicRecorderError("no-device", "No microphone is available.");
}

export class MicRecorder {
  private stream: MediaStream | null = null;
  private recorder: MediaRecorder | null = null;
  private chunks: BlobPart[] = [];

  async start(): Promise<void> {
    const mimeType = getSupportedMimeType();
    if (!mimeType) {
      throw new MicRecorderError(
        "unsupported-browser",
        "Voice input isn't supported in this browser.",
      );
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: SPEECH_AUDIO_CONSTRAINTS });
    } catch (err) {
      throw toMicRecorderError(err);
    }

    this.chunks = [];
    this.recorder = new MediaRecorder(this.stream, { mimeType });
    this.recorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.chunks.push(e.data);
    };
    this.recorder.start();
  }

  /** Resolves with the recorded clip once the recorder has fully flushed. */
  stop(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.recorder) {
        reject(new MicRecorderError("recorder-error", "No active recording."));
        return;
      }
      const mimeType = this.recorder.mimeType;
      this.recorder.onstop = () => {
        this.releaseStream();
        resolve(new Blob(this.chunks, { type: mimeType }));
      };
      this.recorder.stop();
    });
  }

  /** Discards without transcribing — used when the drawer closes mid-recording. */
  cancel(): void {
    if (this.recorder && this.recorder.state !== "inactive") {
      this.recorder.stop();
    }
    this.releaseStream();
  }

  private releaseStream(): void {
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
  }
}
