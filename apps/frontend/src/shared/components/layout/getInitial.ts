const FALLBACK_INITIAL = "A";

export const getInitial = (displayName: string): string =>
  displayName.trim().charAt(0).toUpperCase() || FALLBACK_INITIAL;
