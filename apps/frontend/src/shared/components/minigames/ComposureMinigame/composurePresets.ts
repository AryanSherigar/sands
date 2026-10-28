// The canvas is sized by its width/height attributes and Tailwind classes.
export const CANVAS_SIZE_PX = 480;
export const RESOLUTION_BEAT_MS = 1200;
export const STRIKE_FLASH_MS = 350;

export interface ComposurePalette {
  background: string;
  ring: string;
  pulse: string;
  key: string;
  danger: string;
}

const FALLBACK_PALETTE: ComposurePalette = {
  background: "rgb(12 12 14)",
  ring: "rgb(161 161 170)",
  pulse: "rgb(237 237 239)",
  key: "rgb(237 237 239)",
  danger: "rgb(232 113 106)",
};

const channelsOf = (styles: CSSStyleDeclaration, name: string): string | null => {
  const channels = styles.getPropertyValue(name).trim();
  return channels ? `rgb(${channels})` : null;
};

// Colours come from the app's CSS variables once, at the start of a run.
export function readPalette(element: Element): ComposurePalette {
  const styles = getComputedStyle(element);
  return {
    background: channelsOf(styles, "--surface-sunken") ?? FALLBACK_PALETTE.background,
    ring: channelsOf(styles, "--content-muted") ?? FALLBACK_PALETTE.ring,
    pulse: channelsOf(styles, "--content") ?? FALLBACK_PALETTE.pulse,
    key: channelsOf(styles, "--content") ?? FALLBACK_PALETTE.key,
    danger: channelsOf(styles, "--danger") ?? FALLBACK_PALETTE.danger,
  };
}
