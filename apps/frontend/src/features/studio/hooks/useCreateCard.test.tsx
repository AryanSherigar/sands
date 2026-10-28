import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import { CARD_TEST_SCENARIO_ID, installCardApi } from "../test/cardApiMock";
import { useCreateCard } from "./useCreateCard";

describe("useCreateCard", () => {
  it("creates a Place as a location card with its name as the first trigger", async () => {
    const api = installCardApi({ entities: [], facts: [] });
    const { result } = renderHook(() => useCreateCard(CARD_TEST_SCENARIO_ID), {
      wrapper: createQueryWrapper(),
    });

    await act(async () => {
      await result.current.createCard({ kind: "place", name: "The Lighthouse" });
    });

    expect(api.entities).toHaveLength(1);
    expect(api.entities[0]).toMatchObject({
      entity_type: "location",
      canonical_name: "The Lighthouse",
      aliases: ["The Lighthouse"],
    });
  });

  it("creates the player card with is_player set", async () => {
    const api = installCardApi({ entities: [], facts: [] });
    const { result } = renderHook(() => useCreateCard(CARD_TEST_SCENARIO_ID), {
      wrapper: createQueryWrapper(),
    });

    await act(async () => {
      await result.current.createCard({ kind: "character", isPlayer: true });
    });

    expect(api.entities[0]).toMatchObject({ entity_type: "character", is_player: true });
  });
});
