import { HTTP_SERVICE_UNAVAILABLE } from "./rate-limit-error";

const ALPHA_PAUSED_CODE = "alpha_paused";
export const ALPHA_PAUSED_MESSAGE =
  "The night desk is closed. Try again later.";

/** The owner paused every turn. Never retried automatically: it clears only
 * when the owner resumes, and retrying meanwhile just adds load. */
export class AlphaPausedError extends Error {
  constructor() {
    super(ALPHA_PAUSED_MESSAGE);
    this.name = "AlphaPausedError";
  }
}

export const isAlphaPausedError = (error: unknown): error is AlphaPausedError =>
  error instanceof AlphaPausedError;

const hasPausedCode = (body: unknown): boolean =>
  typeof body === "object" &&
  body !== null &&
  (body as { code?: unknown }).code === ALPHA_PAUSED_CODE;

/** Returns an AlphaPausedError when a response is the pause refusal, else null. */
export const parseAlphaPausedError = (
  status: number,
  body: unknown,
): AlphaPausedError | null =>
  status === HTTP_SERVICE_UNAVAILABLE && hasPausedCode(body)
    ? new AlphaPausedError()
    : null;
