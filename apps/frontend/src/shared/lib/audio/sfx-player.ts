import { SensoryCueId } from "@/shared/constants/sensory-cues";
import { synthesizeCue } from "./sfx-synth";

const SFX_FILE_URL_PREFIX = "/audio/sfx/";
const SFX_FILE_EXTENSION = ".mp3";
const AUDIO_CONTENT_TYPE_PREFIX = "audio/";

export type SfxFileLoader = (url: string) => Promise<ArrayBuffer | null>;

// Only a real audio response counts. A static host that answers a missing file
// with its single-page-app shell (200, text/html) is treated as "no file", the
// same as a 404, so the decoder never has to choke on HTML.
export const fetchSfxFile: SfxFileLoader = async (url) => {
  const response = await fetch(url);
  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok || !contentType.startsWith(AUDIO_CONTENT_TYPE_PREFIX)) {
    return null;
  }
  return response.arrayBuffer();
};

type DecodingContext = BaseAudioContext;

// Gives each cue its buffer: a real recording at `/audio/sfx/{id}.mp3` when one
// ships, otherwise the synthesised sound. The first answer for a cue is kept, so
// a missing or broken file is asked for once and never again this session.
export class SfxPlayer {
  private readonly buffers = new Map<SensoryCueId, Promise<AudioBuffer>>();

  constructor(
    private readonly context: DecodingContext,
    private readonly loadFile: SfxFileLoader = fetchSfxFile,
  ) {}

  public getBuffer(cue: SensoryCueId): Promise<AudioBuffer> {
    const cached = this.buffers.get(cue);
    if (cached) return cached;
    const pending = this.loadPreferredBuffer(cue);
    this.buffers.set(cue, pending);
    return pending;
  }

  public preload(cues: readonly SensoryCueId[]): void {
    for (const cue of cues) void this.getBuffer(cue);
  }

  private async loadPreferredBuffer(cue: SensoryCueId): Promise<AudioBuffer> {
    const recorded = await this.decodeRecording(cue);
    return recorded ?? synthesizeCue(this.context, cue);
  }

  private async decodeRecording(cue: SensoryCueId): Promise<AudioBuffer | null> {
    try {
      const bytes = await this.loadFile(
        `${SFX_FILE_URL_PREFIX}${cue}${SFX_FILE_EXTENSION}`,
      );
      if (!bytes) return null;
      return await this.context.decodeAudioData(bytes);
    } catch {
      return null;
    }
  }
}
