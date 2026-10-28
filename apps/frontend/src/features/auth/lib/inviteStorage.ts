const INVITE_STORAGE_KEY = "alpha_invite_code";
const INVITE_QUERY_PARAM = "invite";

// NOTE: sessionStorage can be blocked or cleared (private windows, in-app
// browsers), so the code is also held in memory for the current page load.
let memoryInvite: string | null = null;

function writeStoredInvite(code: string): void {
  try {
    window.sessionStorage.setItem(INVITE_STORAGE_KEY, code);
  } catch {
    // NOTE: falling back to the in-memory copy is the intended behaviour.
  }
}

function readStoredInvite(): string | null {
  try {
    return window.sessionStorage.getItem(INVITE_STORAGE_KEY);
  } catch {
    return null;
  }
}

function removeStoredInvite(): void {
  try {
    window.sessionStorage.removeItem(INVITE_STORAGE_KEY);
  } catch {
    // NOTE: nothing was stored if storage is unavailable.
  }
}

export function captureInviteFromUrl(
  search: string = window.location.search,
): void {
  const code = new URLSearchParams(search).get(INVITE_QUERY_PARAM);
  if (!code) return;
  memoryInvite = code;
  writeStoredInvite(code);
}

export function readInvite(): string | null {
  return readStoredInvite() ?? memoryInvite;
}

export function clearInvite(): void {
  memoryInvite = null;
  removeStoredInvite();
}
