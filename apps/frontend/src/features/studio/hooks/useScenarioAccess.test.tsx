import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { useScenarioAccess } from "./useScenarioAccess";

const SCENARIO_ID = "scenario-1";

describe("useScenarioAccess", () => {
  it("lists the people who can play a private story", async () => {
    server.use(
      http.get("*/v1/scenarios/scenario-1/access", () =>
        HttpResponse.json([{ user_id: "user-1", display_name: "Ada" }]),
      ),
    );
    const { result } = renderHook(() => useScenarioAccess(SCENARIO_ID), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.members).toHaveLength(1));
    expect(result.current.members[0].display_name).toBe("Ada");
  });

  it("creates an invite link", async () => {
    server.use(
      http.get("*/v1/scenarios/scenario-1/access", () => HttpResponse.json([])),
      http.post("*/v1/scenarios/scenario-1/invites", () =>
        HttpResponse.json(
          { url: "https://sands.test/invite/abc", expires_at: "2026-10-27T00:00:00Z" },
          { status: 201 },
        ),
      ),
    );
    const { result } = renderHook(() => useScenarioAccess(SCENARIO_ID), {
      wrapper: createQueryWrapper(),
    });

    let invite: { url: string } | undefined;
    await act(async () => {
      invite = await result.current.createInviteAsync();
    });

    expect(invite?.url).toBe("https://sands.test/invite/abc");
  });

  it("removes a person's access and refreshes the list", async () => {
    let members = [{ user_id: "user-1", display_name: "Ada" }];
    server.use(
      http.get("*/v1/scenarios/scenario-1/access", () =>
        HttpResponse.json(members),
      ),
      http.delete("*/v1/scenarios/scenario-1/access/user-1", () => {
        members = [];
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { result } = renderHook(() => useScenarioAccess(SCENARIO_ID), {
      wrapper: createQueryWrapper(),
    });
    await waitFor(() => expect(result.current.members).toHaveLength(1));

    await act(async () => {
      await result.current.removeAccessAsync("user-1");
    });

    await waitFor(() => expect(result.current.members).toHaveLength(0));
  });
});
