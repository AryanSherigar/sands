import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { useSignInModalStore } from "@/shared/stores/signInModal.store";
import { useRequireAuth } from "../useRequireAuth";

describe("useRequireAuth", () => {
  beforeEach(() => {
    useAuthStore.setState({ isAuthenticated: false });
    useSignInModalStore.setState({ trigger: null, resolvePending: null });
  });

  it("resolves true without opening the modal when signed in", async () => {
    useAuthStore.setState({ isAuthenticated: true });
    const { result } = renderHook(() => useRequireAuth("save"));
    await expect(result.current()).resolves.toBe(true);
    expect(useSignInModalStore.getState().trigger).toBeNull();
  });

  it("opens the modal with its trigger and resolves when settled", async () => {
    const { result } = renderHook(() => useRequireAuth("review"));
    let pending: Promise<boolean> = Promise.resolve(false);
    act(() => {
      pending = result.current();
    });
    expect(useSignInModalStore.getState().trigger).toBe("review");
    act(() => useSignInModalStore.getState().settle(true));
    await expect(pending).resolves.toBe(true);
    expect(useSignInModalStore.getState().trigger).toBeNull();
  });

  it("resolves false when the modal is dismissed", async () => {
    const { result } = renderHook(() => useRequireAuth("create"));
    let pending: Promise<boolean> = Promise.resolve(true);
    act(() => {
      pending = result.current();
    });
    act(() => useSignInModalStore.getState().settle(false));
    await expect(pending).resolves.toBe(false);
  });
});
