import { emitAlphaEvent } from "./alpha-events";

const SAFE_CODE_PATTERN = /^[A-Za-z0-9_./:-]{1,120}$/;
const UUID_SEGMENT_PATTERN =
  /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;
const UNKNOWN_MESSAGE_CODE = "unknown";
const UNKNOWN_ROUTE = "/";

export function toMessageCode(error: unknown): string {
  if (typeof error !== "object" || error === null) return UNKNOWN_MESSAGE_CODE;
  const code = (error as { code?: unknown }).code;
  if (typeof code === "string" && SAFE_CODE_PATTERN.test(code)) return code;
  const name = (error as { name?: unknown }).name;
  if (typeof name === "string" && SAFE_CODE_PATTERN.test(name)) return name;
  return UNKNOWN_MESSAGE_CODE;
}

export function toRouteLabel(pathname: string): string {
  const label = pathname.replace(UUID_SEGMENT_PATTERN, ":id");
  return SAFE_CODE_PATTERN.test(label) ? label : UNKNOWN_ROUTE;
}

export function emitClientError(kind: string, error: unknown): void {
  emitAlphaEvent("client_error", {
    kind,
    route: toRouteLabel(window.location.pathname),
    message_code: toMessageCode(error),
  });
}
