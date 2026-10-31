import { act, renderHook } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { useGenerateMap } from "../useGenerateMap";

const SCENARIO_ID = "scenario-1";
const REGION_URL = "https://cdn.example/scenario-maps/regions.png";
const ART_URL = "https://cdn.example/scenario-maps/art.webp";
const REGION_SIZE = { width: 1792, height: 1344 };
const PNG_BYTES = new Uint8Array([0x89, 0x50, 0x4e, 0x47]);

const regionsHandler = () =>
  http.post(`*/v1/scenarios/${SCENARIO_ID}/strategy-map/generate-regions`, () =>
    HttpResponse.json({ region_image_url: REGION_URL, ...REGION_SIZE }),
  );
const pngHandler = () =>
  http.get(REGION_URL, () => new HttpResponse(PNG_BYTES, { headers: { "Content-Type": "image/png" } }));

describe("useGenerateMap", () => {
  it("runs regions then art and returns the art as the picture", async () => {
    let artDescription: FormDataEntryValue | null = null;
    server.use(
      regionsHandler(),
      pngHandler(),
      http.post(`*/v1/scenarios/${SCENARIO_ID}/strategy-map/generate-art`, async ({ request }) => {
        artDescription = (await request.formData()).get("description");
        return HttpResponse.json({ picture_url: ART_URL, ...REGION_SIZE });
      }),
    );
    const { result } = renderHook(() => useGenerateMap(SCENARIO_ID), { wrapper: createQueryWrapper() });

    let generated;
    await act(async () => {
      generated = await result.current.generate("a desert empire");
    });

    expect(generated).toMatchObject({ hasArt: true, picture: { url: ART_URL, size: REGION_SIZE } });
    expect((generated as unknown as { regionImage: File }).regionImage.name).toBe("generated-regions.png");
    expect((generated as unknown as { regionImage: File }).regionImage.type).toBe("image/png");
    expect(artDescription).toBe("a desert empire");
  });

  it("falls back to the region image when the art step fails", async () => {
    server.use(
      regionsHandler(),
      pngHandler(),
      http.post(`*/v1/scenarios/${SCENARIO_ID}/strategy-map/generate-art`, () =>
        HttpResponse.json({ detail: "Image generation is temporarily unavailable" }, { status: 502 }),
      ),
    );
    const { result } = renderHook(() => useGenerateMap(SCENARIO_ID), { wrapper: createQueryWrapper() });

    let generated;
    await act(async () => {
      generated = await result.current.generate("a desert empire");
    });

    expect(generated).toMatchObject({ hasArt: false, picture: { url: REGION_URL, size: REGION_SIZE } });
  });

  it("surfaces an error message when the regions step fails", async () => {
    server.use(
      http.post(`*/v1/scenarios/${SCENARIO_ID}/strategy-map/generate-regions`, () =>
        HttpResponse.json({ detail: "Image generation is temporarily unavailable" }, { status: 502 }),
      ),
    );
    const { result } = renderHook(() => useGenerateMap(SCENARIO_ID), { wrapper: createQueryWrapper() });

    await act(async () => {
      await result.current.generate("a desert empire").catch(() => undefined);
    });

    expect(result.current.errorMessage).toBe("Image generation is temporarily unavailable");
  });
});
