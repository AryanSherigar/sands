import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { server } from "@/test/msw/server";
import type { AlphaSurveyRequest } from "@/shared/types/alphaSurvey.types";
import { submitAlphaSurvey } from "../alphaSurvey.api";

const EXPIRED_TOKEN = "expired-token";
const FRESH_TOKEN = "fresh-token";
const SURVEY_REQUEST = { kind: "post_run", answers: {} } as AlphaSurveyRequest;

describe("submitAlphaSurvey with an expired access token", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: EXPIRED_TOKEN });
  });

  it("refreshes once and resubmits instead of failing with a 401", async () => {
    const seenAuthorization: (string | null)[] = [];
    let refreshCount = 0;
    server.use(
      http.post("*/v1/auth/refresh", () => {
        refreshCount += 1;
        return HttpResponse.json({
          access_token: FRESH_TOKEN,
          user: { user_id: "user-1", display_name: "T" },
        });
      }),
      http.post("*/v1/alpha/survey", ({ request }) => {
        const authorization = request.headers.get("Authorization");
        seenAuthorization.push(authorization);
        if (authorization === `Bearer ${FRESH_TOKEN}`) {
          return HttpResponse.json({ kind: "post_run" }, { status: 201 });
        }
        return new HttpResponse(null, { status: 401 });
      }),
    );

    const result = await submitAlphaSurvey(SURVEY_REQUEST);

    expect(result.kind).toBe("post_run");
    expect(refreshCount).toBe(1);
    expect(seenAuthorization).toEqual([
      `Bearer ${EXPIRED_TOKEN}`,
      `Bearer ${FRESH_TOKEN}`,
    ]);
  });
});
