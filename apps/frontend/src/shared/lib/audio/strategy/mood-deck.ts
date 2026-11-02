export const MOOD_FADE_STEP_MS = 100;
const CHANNEL_COUNT = 2;
const FULL_VOLUME = 1;

export interface MoodDeckOptions {
  fadeSeconds: number;
  attachChannel: (element: HTMLAudioElement) => void;
  resolveFallbackUrl: (url: string) => string | null;
}

function tryPlay(element: HTMLAudioElement): void {
  try {
    const result = element.play();
    if (result && typeof result.catch === "function") result.catch(() => {});
  } catch {
    // NOTE: environments without a media implementation (e.g. JSDOM) cannot play; skipping is correct.
  }
}

export class MoodDeck {
  private readonly channels: HTMLAudioElement[] = [];
  private activeIndex = -1;
  private fadeTimer: ReturnType<typeof setInterval> | null = null;

  constructor(private readonly options: MoodDeckOptions) {}

  private channelAt(index: number): HTMLAudioElement {
    const existing = this.channels[index];
    if (existing) return existing;
    const element = new Audio();
    element.loop = true;
    element.preload = "auto";
    element.crossOrigin = "anonymous";
    element.volume = 0;
    element.onerror = () => this.fallBack(element);
    this.options.attachChannel(element);
    this.channels[index] = element;
    return element;
  }

  private fallBack(element: HTMLAudioElement): void {
    const fallbackUrl = this.options.resolveFallbackUrl(element.src);
    if (!fallbackUrl || element.src.endsWith(fallbackUrl)) return;
    element.src = fallbackUrl;
    tryPlay(element);
  }

  crossfadeTo(url: string, shouldPlay: boolean): void {
    const outgoing = this.activeIndex >= 0 ? this.channels[this.activeIndex] : undefined;
    this.activeIndex = (this.activeIndex + 1) % CHANNEL_COUNT;
    const incoming = this.channelAt(this.activeIndex);
    incoming.src = url;
    incoming.volume = 0;
    if (shouldPlay) tryPlay(incoming);
    this.fade(incoming, outgoing);
  }

  private fade(incoming: HTMLAudioElement, outgoing: HTMLAudioElement | undefined): void {
    if (this.fadeTimer) clearInterval(this.fadeTimer);
    const totalSteps = Math.max(1, Math.round((this.options.fadeSeconds * 1000) / MOOD_FADE_STEP_MS));
    let step = 0;
    this.fadeTimer = setInterval(() => {
      step += 1;
      const progress = Math.min(1, step / totalSteps);
      incoming.volume = FULL_VOLUME * progress;
      if (outgoing) outgoing.volume = FULL_VOLUME * (1 - progress);
      if (progress >= 1) this.finishFade(outgoing);
    }, MOOD_FADE_STEP_MS);
  }

  private finishFade(outgoing: HTMLAudioElement | undefined): void {
    if (this.fadeTimer) clearInterval(this.fadeTimer);
    this.fadeTimer = null;
    if (!outgoing) return;
    outgoing.pause();
    outgoing.removeAttribute("src");
  }

  play(): void {
    const active = this.activeIndex >= 0 ? this.channels[this.activeIndex] : undefined;
    if (active && active.paused) tryPlay(active);
  }

  destroy(): void {
    if (this.fadeTimer) clearInterval(this.fadeTimer);
    this.fadeTimer = null;
    this.channels.forEach((element) => {
      element.onerror = null;
      element.pause();
      element.removeAttribute("src");
    });
    this.channels.length = 0;
    this.activeIndex = -1;
  }
}
