import { describe, expect, it, vi } from "vitest";
import { attachComposureControls, keyFromCode } from "../composureControls";

const press = (code: string, init: KeyboardEventInit = {}): KeyboardEvent => {
  const event = new KeyboardEvent("keydown", { code, cancelable: true, ...init });
  window.dispatchEvent(event);
  return event;
};

describe("composure controls", () => {
  it.each([
    ["KeyW", "W"],
    ["ArrowUp", "W"],
    ["KeyA", "A"],
    ["ArrowLeft", "A"],
    ["KeyS", "S"],
    ["ArrowDown", "S"],
    ["KeyD", "D"],
    ["ArrowRight", "D"],
  ])("maps the physical key %s to slot %s", (code, key) => {
    expect(keyFromCode(code)).toBe(key);
  });

  it("ignores keys that are not part of the game", () => {
    expect(keyFromCode("KeyQ")).toBeNull();
    expect(keyFromCode("Space")).toBeNull();
  });

  it("reports an allowed key with the event timestamp", () => {
    const onPress = vi.fn();
    const detach = attachComposureControls(window, ["W", "A", "S", "D"], onPress);

    const event = press("KeyD");

    expect(onPress).toHaveBeenCalledWith("D", event.timeStamp);
    detach();
  });

  it("ignores auto-repeat", () => {
    const onPress = vi.fn();
    const detach = attachComposureControls(window, ["W"], onPress);

    press("KeyW", { repeat: true });

    expect(onPress).not.toHaveBeenCalled();
    detach();
  });

  it("ignores keys outside the scenario's key set", () => {
    const onPress = vi.fn();
    const detach = attachComposureControls(window, ["W"], onPress);

    const event = press("KeyS");

    expect(onPress).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);
    detach();
  });

  it("stops the page scrolling on an arrow key it handles", () => {
    const detach = attachComposureControls(window, ["W"], vi.fn());

    expect(press("ArrowUp").defaultPrevented).toBe(true);
    detach();
  });

  it("stops listening once detached", () => {
    const onPress = vi.fn();
    const detach = attachComposureControls(window, ["W"], onPress);
    detach();

    press("KeyW");

    expect(onPress).not.toHaveBeenCalled();
  });
});
