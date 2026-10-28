import { QueryClient } from "@tanstack/react-query";
import { AxiosError, AxiosHeaders } from "axios";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useStudioStore } from "../../stores/studio.store";
import {
  disableEditGuard,
  enableEditGuard,
  isEditConflictError,
  refreshEditStamp,
  runGuardedWrite,
  waitForPendingWrites,
} from "../editGuard";

const SCENARIO_ID = "scenario-1";
const FIRST_STAMP = "2026-10-27T10:00:00Z";
const SECOND_STAMP = "2026-10-27T10:00:05Z";

const buildConflict = (code: string): AxiosError => {
  const headers = new AxiosHeaders();
  return new AxiosError("conflict", "ERR_BAD_REQUEST", undefined, undefined, {
    status: 409,
    statusText: "Conflict",
    headers,
    config: { headers },
    data: { detail: "changed", code },
  });
};

const seedStamp = (queryClient: QueryClient, stamp: string): void => {
  queryClient.setQueryData(["scenario", SCENARIO_ID], { content_edited_at: stamp });
};

describe("editGuard", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient();
    useStudioStore.getState().setHasEditConflict(false);
  });

  afterEach(() => {
    disableEditGuard(SCENARIO_ID);
  });

  it("passes no stamp through when the guard is off", async () => {
    seedStamp(queryClient, FIRST_STAMP);
    const stamps: Array<string | undefined> = [];
    await runGuardedWrite(queryClient, SCENARIO_ID, async (stamp) => {
      stamps.push(stamp);
    });
    expect(stamps).toEqual([undefined]);
  });

  it("hands the cached content_edited_at to the write when the guard is on", async () => {
    enableEditGuard(SCENARIO_ID);
    seedStamp(queryClient, FIRST_STAMP);
    const stamps: Array<string | undefined> = [];
    await runGuardedWrite(queryClient, SCENARIO_ID, async (stamp) => {
      stamps.push(stamp);
    });
    expect(stamps).toEqual([FIRST_STAMP]);
  });

  it("runs chained writes one at a time so each sees the stamp the previous one left", async () => {
    enableEditGuard(SCENARIO_ID);
    seedStamp(queryClient, FIRST_STAMP);
    const seen: Array<string | undefined> = [];
    const slowWrite = runGuardedWrite(queryClient, SCENARIO_ID, async (stamp) => {
      seen.push(stamp);
      await new Promise((resolve) => setTimeout(resolve, 20));
      seedStamp(queryClient, SECOND_STAMP);
    });
    const nextWrite = runGuardedWrite(queryClient, SCENARIO_ID, async (stamp) => {
      seen.push(stamp);
    });
    await Promise.all([slowWrite, nextWrite]);
    expect(seen).toEqual([FIRST_STAMP, SECOND_STAMP]);
  });

  it("flags a scenario_edit_conflict and rethrows without retrying", async () => {
    enableEditGuard(SCENARIO_ID);
    seedStamp(queryClient, FIRST_STAMP);
    let attempts = 0;
    const attempt = runGuardedWrite(queryClient, SCENARIO_ID, async () => {
      attempts += 1;
      throw buildConflict("scenario_edit_conflict");
    });
    await expect(attempt).rejects.toBeInstanceOf(AxiosError);
    expect(attempts).toBe(1);
    expect(useStudioStore.getState().hasEditConflict).toBe(true);
  });

  it("does not flag other 409 errors as an edit conflict", async () => {
    enableEditGuard(SCENARIO_ID);
    await expect(
      runGuardedWrite(queryClient, SCENARIO_ID, async () => {
        throw buildConflict("something_else");
      }),
    ).rejects.toBeInstanceOf(AxiosError);
    expect(useStudioStore.getState().hasEditConflict).toBe(false);
    expect(isEditConflictError(buildConflict("scenario_edit_conflict"))).toBe(true);
    expect(isEditConflictError(new Error("x"))).toBe(false);
  });

  it("keeps the queue moving after a failed write", async () => {
    enableEditGuard(SCENARIO_ID);
    const failed = runGuardedWrite(queryClient, SCENARIO_ID, async () => {
      throw new Error("boom");
    });
    await expect(failed).rejects.toThrow("boom");
    await expect(
      runGuardedWrite(queryClient, SCENARIO_ID, async () => "ok"),
    ).resolves.toBe("ok");
  });

  it("refetches the scenario after a delete because delete returns no stamp", async () => {
    enableEditGuard(SCENARIO_ID);
    seedStamp(queryClient, FIRST_STAMP);
    server.use(
      http.get(`*/v1/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json({ scenario_id: SCENARIO_ID, content_edited_at: SECOND_STAMP }),
      ),
    );
    await runGuardedWrite(queryClient, SCENARIO_ID, async () => undefined, {
      shouldRefreshStamp: true,
    });
    const cached = queryClient.getQueryData<{ content_edited_at: string }>([
      "scenario",
      SCENARIO_ID,
    ]);
    expect(cached?.content_edited_at).toBe(SECOND_STAMP);
  });

  it("refreshEditStamp only updates the stamp field of the cached scenario", async () => {
    queryClient.setQueryData(["scenario", SCENARIO_ID], {
      scenario_id: SCENARIO_ID,
      title: "Local",
      content_edited_at: FIRST_STAMP,
    });
    server.use(
      http.get(`*/v1/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json({ scenario_id: SCENARIO_ID, title: "Server", content_edited_at: SECOND_STAMP }),
      ),
    );
    await refreshEditStamp(queryClient, SCENARIO_ID);
    expect(queryClient.getQueryData(["scenario", SCENARIO_ID])).toMatchObject({
      title: "Local",
      content_edited_at: SECOND_STAMP,
    });
  });

  it("waitForPendingWrites resolves only after queued guarded writes finish", async () => {
    enableEditGuard(SCENARIO_ID);
    seedStamp(queryClient, FIRST_STAMP);
    const finished: string[] = [];
    const slowWrite = new Promise<string>((resolve) =>
      setTimeout(() => resolve("done"), 20),
    );
    void runGuardedWrite(queryClient, SCENARIO_ID, async () => {
      const value = await slowWrite;
      finished.push(value);
      return value;
    });

    await waitForPendingWrites(SCENARIO_ID);

    expect(finished).toEqual(["done"]);
    disableEditGuard(SCENARIO_ID);
  });

  it("waitForPendingWrites resolves at once when nothing is queued", async () => {
    await expect(waitForPendingWrites("scenario-with-no-writes")).resolves.toBeUndefined();
  });
});
