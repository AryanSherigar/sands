import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildEntityFixture } from "../test/cardApiMock";
import { createGuideWrapper } from "../test/guideHookWrapper";
import { buildScenarioFixture, installStudioApi } from "../test/studioApiMock";
import { useValueOptions } from "./useValueOptions";

describe("useValueOptions", () => {
  it("offers tracked values and card values together", async () => {
    installStudioApi({
      scenario: buildScenarioFixture({
        mode: "master",
        state_schema: { oil: { type: "number", label: "Lantern oil" } },
      }),
      entities: [
        buildEntityFixture({
          entity_id: "guard",
          canonical_name: "Guard",
          attributes_schema: { health: { type: "number", label: "Health" } },
        }),
      ],
    });
    const { Wrapper } = createGuideWrapper();
    const { result } = renderHook(() => useValueOptions(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.map((option) => option.label)).toEqual(["Lantern oil", "Guard's Health"]));
  });
});
