import { act, renderHook } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { MapDocument } from "@/shared/types/strategy-map.types";
import { useSaveRegionMap } from "./useSaveRegionMap";

const DOCUMENT: MapDocument = {
  schema_version: 1,
  source: "color_image",
  width: 40,
  height: 40,
  image_url: "https://cdn.example/map.png",
  regions: [],
  roads: [],
};

describe("useSaveRegionMap", () => {
  it("sends the traced map document and returns what the server stored", async () => {
    let received: unknown = null;
    server.use(
      http.put("*/v1/scenarios/scenario-1/strategy-map", async ({ request }) => {
        received = await request.json();
        return HttpResponse.json(DOCUMENT);
      }),
    );
    const { result } = renderHook(() => useSaveRegionMap("scenario-1"), {
      wrapper: createQueryWrapper(),
    });
    let saved: MapDocument | undefined;
    await act(async () => {
      saved = await result.current.mutateAsync(DOCUMENT);
    });
    expect(received).toEqual(DOCUMENT);
    expect(saved).toEqual(DOCUMENT);
  });

  it("surfaces the server's validation message", async () => {
    server.use(
      http.put("*/v1/scenarios/scenario-1/strategy-map", () =>
        HttpResponse.json({ detail: "Map is not connected" }, { status: 422 }),
      ),
    );
    const { result } = renderHook(() => useSaveRegionMap("scenario-1"), {
      wrapper: createQueryWrapper(),
    });
    await act(async () => {
      await expect(result.current.mutateAsync(DOCUMENT)).rejects.toThrow();
    });
    expect(result.current.errorMessage).toBe("Map is not connected");
  });
});
