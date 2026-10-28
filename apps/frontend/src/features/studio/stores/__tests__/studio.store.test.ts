import { beforeEach, describe, expect, it } from "vitest";
import { useStudioStore } from "../studio.store";

describe("useStudioStore save state", () => {
  beforeEach(() => {
    useStudioStore.getState().resetSaveState();
  });

  it("keeps the last saved time while a new save is in flight", () => {
    const savedAt = new Date("2026-10-27T10:00:00Z");
    useStudioStore.getState().setSaveState(false, savedAt);
    useStudioStore.getState().setSaveState(true);

    const { isSaving, lastSaved } = useStudioStore.getState();
    expect(isSaving).toBe(true);
    expect(lastSaved).toEqual(savedAt);
  });

  it("clears both the saving flag and the last saved time on reset", () => {
    useStudioStore.getState().setSaveState(true, new Date());
    useStudioStore.getState().resetSaveState();

    expect(useStudioStore.getState().isSaving).toBe(false);
    expect(useStudioStore.getState().lastSaved).toBeNull();
  });
});
