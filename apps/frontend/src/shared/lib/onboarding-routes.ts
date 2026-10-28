export const WELCOME_PATH = "/welcome";
const DISCOVER_PATH = "/discover";
export const ONBOARDING_REDIRECT_PARAM = "redirect";
export const ONBOARDING_REDO_PARAM = "redo";
export const SETTINGS_PATH = "/settings";
const GENRE_PARAM = "genre";

export function sanitizeRedirectTarget(rawTarget: string | null): string | null {
  if (!rawTarget) return null;
  const isInternalPath = rawTarget.startsWith("/") && !rawTarget.startsWith("//");
  const isWelcomePath = rawTarget.startsWith(WELCOME_PATH);
  if (!isInternalPath || isWelcomePath) return null;
  return rawTarget;
}

export function buildWelcomeHref(redirectTarget: string): string {
  const safeTarget = sanitizeRedirectTarget(redirectTarget);
  if (!safeTarget || safeTarget === "/") return WELCOME_PATH;
  const params = new URLSearchParams({ [ONBOARDING_REDIRECT_PARAM]: safeTarget });
  return `${WELCOME_PATH}?${params.toString()}`;
}

export function buildDiscoverHref(genres: string[]): string {
  if (genres.length === 0) return DISCOVER_PATH;
  const params = new URLSearchParams();
  genres.forEach((genre) => params.append(GENRE_PARAM, genre));
  return `${DISCOVER_PATH}?${params.toString()}`;
}
