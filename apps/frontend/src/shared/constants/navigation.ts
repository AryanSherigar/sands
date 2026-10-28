export interface PrimaryNavLink {
  to: string;
  label: string;
  isExact: boolean;
}

export const STUDIO_PATH = "/studio";

const PRIMARY_NAV_LINKS: readonly PrimaryNavLink[] = [
  { to: "/", label: "Home", isExact: true },
  { to: "/discover", label: "Discover", isExact: false },
  { to: STUDIO_PATH, label: "Studio", isExact: false },
];

export const getPrimaryNavLinks = (
  isAlphaMode: boolean,
): readonly PrimaryNavLink[] =>
  isAlphaMode
    ? PRIMARY_NAV_LINKS.filter((link) => link.to !== STUDIO_PATH)
    : PRIMARY_NAV_LINKS;

export const DESKTOP_MEDIA_QUERY = "(min-width: 768px)";
export const SCROLL_CONDENSE_THRESHOLD_PX = 24;
export const HERO_SCROLL_THRESHOLD_PX = 320;
export const KEYBOARD_VIEWPORT_RATIO = 0.75;
export const SEARCH_FOCUS_SHORTCUT_KEY = "/";
export const SKIP_LINK_TARGET_ID = "main-content";
export const SEARCH_PLACEHOLDER = "Search scenarios, authors, genres...";
export const DISCOVER_PATH = "/discover";
export const SIGN_IN_PATH = "/login";
export const PLAYTEST_SEARCH_PARAM = "playtest";
export const PLAYTEST_SEARCH_VALUE = "1";

export const buildPlaytestSetupPath = (scenarioId: string): string =>
  `/setup/${scenarioId}?${PLAYTEST_SEARCH_PARAM}=${PLAYTEST_SEARCH_VALUE}`;
