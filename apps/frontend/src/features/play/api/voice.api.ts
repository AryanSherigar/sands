import { useAuthStore } from "@/features/auth/stores/auth.store";
import {
  buildTrsAuthHeaders,
  readRateLimitError,
} from "@/shared/lib/sse-client";

const TRS_BASE_URL = import.meta.env.VITE_TRS_URL || "http://localhost:8001";

class VoiceTranscriptionError extends Error {}

interface TranscriptionResponse {
  transcript: string;
}

/** One-shot upload-and-transcribe call, not a React Query mutation — this is
 * an imperative action tied to a recording gesture, the same way submitTurn
 * itself isn't cached/query-shaped data. */
export async function transcribeAudio(
  audioBlob: Blob,
  playthroughId?: string,
): Promise<string> {
  const formData = new FormData();
  formData.append("file", audioBlob, "action.webm");
  if (playthroughId) formData.append("playthrough_id", playthroughId);

  const accessToken = useAuthStore.getState().accessToken;
  const response = await fetch(`${TRS_BASE_URL}/v1/voice/transcribe`, {
    method: "POST",
    headers: buildTrsAuthHeaders(accessToken),
    body: formData,
  });

  if (!response.ok) {
    const rateLimitError = await readRateLimitError(response);
    if (rateLimitError) throw rateLimitError;
    throw new VoiceTranscriptionError(
      `Transcription failed: ${response.status}`,
    );
  }
  const data = (await response.json()) as TranscriptionResponse;
  return data.transcript;
}

export async function fetchWelcomeClosing(
  playthroughId: string,
  signal: AbortSignal,
): Promise<ArrayBuffer> {
  const response = await fetch(
    `${TRS_BASE_URL}/v1/voice/welcome/${playthroughId}`,
    {
      method: "POST",
      signal,
      headers: buildTrsAuthHeaders(useAuthStore.getState().accessToken),
    },
  );
  if (!response.ok)
    throw new Error(`Welcome voice unavailable: ${response.status}`);
  return response.arrayBuffer();
}
