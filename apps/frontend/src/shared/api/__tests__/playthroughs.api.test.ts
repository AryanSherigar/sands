import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { START_PLAYTHROUGH_TIMEOUT_MS } from "@/shared/constants/api";
import { apiClient } from "@/shared/lib/api-client";
import { createPlaythrough } from "../playthroughs.api";

describe("createPlaythrough", () => {
  it("waits longer than the default request timeout, since starting a strategy scenario is slow", async () => {
    let configuredTimeout: number | undefined;
    apiClient.interceptors.request.use((config) => {
      if (config.url === "/v1/playthroughs") configuredTimeout = config.timeout;
      return config;
    });
    server.use(
      http.post("*/v1/playthroughs", () => HttpResponse.json({ playthrough_id: "p1" })),
    );

    await createPlaythrough({ scenario_id: "s1" } as never);

    expect(START_PLAYTHROUGH_TIMEOUT_MS).toBeGreaterThan(8000);
    expect(configuredTimeout).toBe(START_PLAYTHROUGH_TIMEOUT_MS);
  });
});
