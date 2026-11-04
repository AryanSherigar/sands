import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { usePersistedAppliedKeys } from "../usePersistedAppliedKeys";

const CHAT_KEY = "sands_studio_assistant_chat:strategy:user-1:scenario-1";
const APPLIED_KEY = `${CHAT_KEY}:applied`;

describe("usePersistedAppliedKeys", () => {
  beforeEach(() => localStorage.clear());

  it("keeps applied keys across a remount", () => {
    const first = renderHook(() => usePersistedAppliedKeys(CHAT_KEY));
    act(() => first.result.current.markApplied("msg-1:0"));
    first.unmount();

    const second = renderHook(() => usePersistedAppliedKeys(CHAT_KEY));

    expect(second.result.current.appliedKeys.has("msg-1:0")).toBe(true);
  });

  it("forgets everything on reset", () => {
    localStorage.setItem(APPLIED_KEY, JSON.stringify(["msg-1:0"]));
    const { result } = renderHook(() => usePersistedAppliedKeys(CHAT_KEY));

    act(() => result.current.resetApplied());

    expect(result.current.appliedKeys.size).toBe(0);
    expect(JSON.parse(localStorage.getItem(APPLIED_KEY) ?? "[]")).toEqual([]);
  });

  it("ignores corrupt storage and does not persist without a chat key", () => {
    localStorage.setItem(APPLIED_KEY, "{broken");
    const corrupt = renderHook(() => usePersistedAppliedKeys(CHAT_KEY));
    expect(corrupt.result.current.appliedKeys.size).toBe(0);

    const anonymous = renderHook(() => usePersistedAppliedKeys(null));
    act(() => anonymous.result.current.markApplied("msg-9:0"));
    expect(anonymous.result.current.appliedKeys.has("msg-9:0")).toBe(true);
    expect(localStorage.getItem("null:applied")).toBeNull();
  });
});
