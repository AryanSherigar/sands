import { AxiosError, type AxiosResponse } from "axios";
import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "../../stores/auth.store";
import {
  isAccountSuspendedError,
  markSuspendedIfRefused,
} from "../accountSuspension";

const refusal = (status: number, code: string): AxiosError =>
  new AxiosError("refused", "ERR_BAD_REQUEST", undefined, undefined, {
    status,
    data: { code },
  } as AxiosResponse);

describe("account suspension detection", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "token",
      isAuthenticated: true,
      isSuspended: false,
      user: null,
    });
  });

  it("recognises a 403 account_suspended refusal", () => {
    expect(isAccountSuspendedError(refusal(403, "account_suspended"))).toBe(true);
  });

  it("ignores other refusals and non-http errors", () => {
    expect(isAccountSuspendedError(refusal(403, "alpha_invite_required"))).toBe(
      false,
    );
    expect(isAccountSuspendedError(refusal(401, "account_suspended"))).toBe(
      false,
    );
    expect(isAccountSuspendedError(new Error("network"))).toBe(false);
  });

  it("signs the user out and remembers why when suspended", () => {
    const handled = markSuspendedIfRefused(refusal(403, "account_suspended"));

    const state = useAuthStore.getState();
    expect(handled).toBe(true);
    expect(state.isAuthenticated).toBe(false);
    expect(state.accessToken).toBeNull();
    expect(state.isSuspended).toBe(true);
  });

  it("leaves the session alone for any other error", () => {
    const handled = markSuspendedIfRefused(new Error("network"));

    expect(handled).toBe(false);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it("clears the suspended flag when someone signs in again", () => {
    useAuthStore.getState().markSuspended();

    useAuthStore.getState().setAuth("jwt", {
      user_id: "u1",
      display_name: "T",
      onboarding_completed: true,
    });

    expect(useAuthStore.getState().isSuspended).toBe(false);
  });
});
