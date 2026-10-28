import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { captureInviteFromUrl, clearInvite, readInvite } from "../inviteStorage";

describe("inviteStorage", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    clearInvite();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("captures the invite query parameter and reads it back", () => {
    captureInviteFromUrl("?invite=abc123");
    expect(readInvite()).toBe("abc123");
  });

  it("ignores a URL without an invite", () => {
    captureInviteFromUrl("?other=1");
    expect(readInvite()).toBeNull();
  });

  it("keeps an earlier invite when a later page load has none", () => {
    captureInviteFromUrl("?invite=abc123");
    captureInviteFromUrl("");
    expect(readInvite()).toBe("abc123");
  });

  it("clears the invite", () => {
    captureInviteFromUrl("?invite=abc123");
    clearInvite();
    expect(readInvite()).toBeNull();
  });

  it("survives a page reload through sessionStorage", () => {
    captureInviteFromUrl("?invite=abc123");
    expect(window.sessionStorage.getItem("alpha_invite_code")).toBe("abc123");
  });

  it("still works within the page load when sessionStorage throws", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    expect(() => captureInviteFromUrl("?invite=abc123")).not.toThrow();
    expect(readInvite()).toBe("abc123");
    expect(() => clearInvite()).not.toThrow();
    expect(readInvite()).toBeNull();
  });
});
