// NOTE: space-separated RGB channels of the DESIGN.md genre accents, kept as
// static class strings so Tailwind can see them. Each scopes --accent to one card.
const NEUTRAL_ACCENT_CLASS = "[--accent:237_237_239]";

const GENRE_ACCENT_CLASSES: Record<string, string> = {
  "High Fantasy": "[--accent:205_187_142]",
  "Sci-Fi": "[--accent:127_184_201]",
  "Adventure/Survival": "[--accent:143_178_122]",
  "Slice of Life": "[--accent:210_155_178]",
  "Noir / Detective": "[--accent:199_154_116]",
  "Post-Apocalyptic/Dystopian": "[--accent:175_174_140]",
  Cyberpunk: "[--accent:197_139_201]",
  Horror: "[--accent:208_119_124]",
  "Historical Fiction": "[--accent:191_163_138]",
  Mystery: "[--accent:142_155_219]",
};

export const getGenreAccentClass = (genre: string | null): string =>
  (genre && GENRE_ACCENT_CLASSES[genre]) || NEUTRAL_ACCENT_CLASS;
