import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useLetterScene } from "../useLetterScene";
import { DEFAULT_LETTER_SCENARIO } from "../../components/StrategyPlayScreen/letter/fixtures/defaultLetterScenario";

describe("useLetterScene hook", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("initializes in reading stage and transitions to drafting on docket choice", () => {
    const onSeal = vi.fn();
    const onClose = vi.fn();
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, onSeal, onClose)
    );

    expect(result.current.stage).toBe("reading");
    expect(result.current.isShelfActive).toBe(false);
    expect(result.current.isMuted).toBe(false);
    expect(result.current.isSealing).toBe(false);

    act(() => {
      result.current.handleSelectDocket("write");
    });

    expect(result.current.stage).toBe("drafting");
    expect(result.current.mode).toBe("direct_quill");
    expect(result.current.toastMessage).toContain("Quill dipped");
  });

  it("sets shelf active and closes modal when docket is set aside", () => {
    const onSeal = vi.fn();
    const onClose = vi.fn();
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, onSeal, onClose)
    );

    act(() => {
      result.current.handleSelectDocket("aside");
    });

    expect(result.current.isShelfActive).toBe(true);
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(result.current.toastMessage).toContain("desk tray");
  });

  it("transitions to scribe mode when scribe docket is chosen", () => {
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, vi.fn(), vi.fn())
    );

    act(() => {
      result.current.handleSelectDocket("scribe");
    });

    expect(result.current.stage).toBe("drafting");
    expect(result.current.mode).toBe("scribe");
    expect(result.current.toastMessage).toContain("Summoning Brother Lucan");
  });

  it("asks the live scribe and records the returned prose as a revision", async () => {
    const requestScribeDraft = vi
      .fn<(instruction: string, currentProse: string) => Promise<string>>()
      .mockResolvedValue("Concerning the fords: we walk the line.\n\nWe remain neighbours.");
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, vi.fn(), vi.fn(), requestScribeDraft)
    );

    await act(async () => {
      await result.current.handleScribeRewrite("Make it firmer on borders");
    });

    expect(requestScribeDraft).toHaveBeenCalledWith(
      "Make it firmer on borders",
      DEFAULT_LETTER_SCENARIO.initialDraft.paragraphs.join("\n\n")
    );
    expect(result.current.activeDraft.paragraphs).toEqual([
      "Concerning the fords: we walk the line.",
      "We remain neighbours.",
    ]);
    expect(result.current.activeDraft.instruction).toBe("Make it firmer on borders");
    expect(result.current.isScribeWorking).toBe(false);
  });

  it("marks the scribe as working while the draft is pending", async () => {
    let resolveDraft: (prose: string) => void = () => undefined;
    const requestScribeDraft = vi.fn(
      () => new Promise<string>((resolve) => { resolveDraft = resolve; })
    );
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, vi.fn(), vi.fn(), requestScribeDraft)
    );

    let pending: Promise<void> | undefined;
    act(() => {
      pending = result.current.handleScribeRewrite("Shorter");
    });
    expect(result.current.isScribeWorking).toBe(true);

    await act(async () => {
      resolveDraft("A shorter reply.");
      await pending;
    });
    expect(result.current.isScribeWorking).toBe(false);
  });

  it("keeps the draft and tells the player when the scribe fails", async () => {
    const requestScribeDraft = vi.fn().mockRejectedValue(new Error("down"));
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, vi.fn(), vi.fn(), requestScribeDraft)
    );

    await act(async () => {
      await result.current.handleScribeRewrite("Firmer");
    });

    expect(result.current.activeDraft).toEqual(DEFAULT_LETTER_SCENARIO.initialDraft);
    expect(result.current.canUndo).toBe(false);
    expect(result.current.toastMessage).toMatch(/scribe could not/i);
    expect(result.current.isScribeWorking).toBe(false);
  });

  it("never invents a draft when no scribe is connected", async () => {
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, vi.fn(), vi.fn())
    );

    await act(async () => {
      await result.current.handleScribeRewrite("Firmer");
    });

    expect(result.current.activeDraft).toEqual(DEFAULT_LETTER_SCENARIO.initialDraft);
    expect(result.current.toastMessage).toMatch(/scribe is not available/i);
  });

  it("refuses an over-long scribe instruction before asking the scribe", async () => {
    const requestScribeDraft = vi.fn().mockResolvedValue("x");
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, vi.fn(), vi.fn(), requestScribeDraft)
    );

    await act(async () => {
      await result.current.handleScribeRewrite("x".repeat(301));
    });

    expect(requestScribeDraft).not.toHaveBeenCalled();
    expect(result.current.toastMessage).toMatch(/300/);
  });

  it("handles undo and redo on draft revisions", async () => {
    const requestScribeDraft = vi.fn().mockResolvedValue("A firmer reply.");
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, vi.fn(), vi.fn(), requestScribeDraft)
    );

    await act(async () => {
      await result.current.handleScribeRewrite("Make it firmer on borders");
    });
    expect(result.current.canUndo).toBe(true);
    expect(result.current.canRedo).toBe(false);

    act(() => {
      result.current.handleUndo();
    });
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(true);
    expect(result.current.activeDraft).toEqual(DEFAULT_LETTER_SCENARIO.initialDraft);

    act(() => {
      result.current.handleRedo();
    });
    expect(result.current.activeDraft.paragraphs).toEqual(["A firmer reply."]);
  });

  it("replaces the whole body with the typed text and can undo it", () => {
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, vi.fn(), vi.fn())
    );

    act(() => {
      result.current.handleUpdateBody("First thought.\n\nSecond thought.");
    });

    expect(result.current.activeDraft.paragraphs).toEqual([
      "First thought.\n\nSecond thought.",
    ]);
    expect(result.current.canUndo).toBe(true);

    act(() => {
      result.current.handleUndo();
    });

    expect(result.current.activeDraft).toEqual(DEFAULT_LETTER_SCENARIO.initialDraft);
  });

  it("seals typed text with its internal blank lines intact", async () => {
    const onSeal = vi.fn().mockResolvedValue(true);
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, onSeal, vi.fn())
    );
    act(() => {
      result.current.handleUpdateBody("First.\n\nSecond.");
    });

    act(() => {
      result.current.handleSealAndSend();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(250);
    });

    expect(onSeal).toHaveBeenCalledWith(
      expect.objectContaining({ finalProse: "First.\n\nSecond." })
    );
  });

  it("seals the real prose, waits for the result, then closes", async () => {
    const onSeal = vi.fn().mockResolvedValue(true);
    const onClose = vi.fn();
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, onSeal, onClose)
    );

    act(() => {
      result.current.handleSealAndSend();
    });
    expect(result.current.isSealing).toBe(true);
    expect(onSeal).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(250);
    });

    expect(onSeal).toHaveBeenCalledWith({
      sceneId: DEFAULT_LETTER_SCENARIO.sceneId,
      finalProse: DEFAULT_LETTER_SCENARIO.initialDraft.paragraphs.join("\n\n"),
      instructionSummary: DEFAULT_LETTER_SCENARIO.initialDraft.instruction,
      revisionCount: 1,
    });
    expect(result.current.isSealing).toBe(false);
    expect(result.current.isShelfActive).toBe(false);
    expect(onClose).toHaveBeenCalled();
  });

  it("keeps the letter open and the draft intact when sealing fails", async () => {
    const onSeal = vi.fn().mockResolvedValue(false);
    const onClose = vi.fn();
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, onSeal, onClose)
    );

    act(() => {
      result.current.handleSealAndSend();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(250);
    });

    expect(onClose).not.toHaveBeenCalled();
    expect(result.current.isSealing).toBe(false);
    expect(result.current.activeDraft).toEqual(DEFAULT_LETTER_SCENARIO.initialDraft);
    expect(result.current.toastMessage).toMatch(/not sent/i);
  });

  it("refuses to seal an empty letter", () => {
    const onSeal = vi.fn();
    const emptyPackage = {
      ...DEFAULT_LETTER_SCENARIO,
      initialDraft: { ...DEFAULT_LETTER_SCENARIO.initialDraft, paragraphs: ["  "] },
    };
    const { result } = renderHook(() => useLetterScene(emptyPackage, onSeal, vi.fn()));

    act(() => {
      result.current.handleSealAndSend();
    });

    expect(result.current.isSealing).toBe(false);
    expect(onSeal).not.toHaveBeenCalled();
    expect(result.current.toastMessage).toMatch(/write something/i);
  });

  it("refuses to seal a letter longer than 1200 characters", () => {
    const onSeal = vi.fn();
    const longPackage = {
      ...DEFAULT_LETTER_SCENARIO,
      initialDraft: {
        ...DEFAULT_LETTER_SCENARIO.initialDraft,
        paragraphs: ["x".repeat(1201)],
      },
    };
    const { result } = renderHook(() => useLetterScene(longPackage, onSeal, vi.fn()));

    act(() => {
      result.current.handleSealAndSend();
    });

    expect(onSeal).not.toHaveBeenCalled();
    expect(result.current.toastMessage).toMatch(/1200/);
  });

  it("toggles mute state and resumes from shelf", () => {
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, vi.fn(), vi.fn())
    );

    expect(result.current.isMuted).toBe(false);

    act(() => {
      result.current.handleToggleMute();
    });
    expect(result.current.isMuted).toBe(true);

    act(() => {
      result.current.handleSelectDocket("aside");
    });
    expect(result.current.isShelfActive).toBe(true);

    act(() => {
      result.current.handleResumeFromShelf();
    });
    expect(result.current.isShelfActive).toBe(false);
  });

  it("responds to keyboard shortcuts in reading and drafting stages", () => {
    const onSeal = vi.fn();
    const onClose = vi.fn();
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, onSeal, onClose)
    );

    // Press '1' to start drafting directly
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "1" }));
    });
    expect(result.current.stage).toBe("drafting");
    expect(result.current.mode).toBe("direct_quill");

    // Press Escape to return to reading
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(result.current.stage).toBe("reading");

    // Press '2' to scribe
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "2" }));
    });
    expect(result.current.stage).toBe("drafting");
    expect(result.current.mode).toBe("scribe");

    // Press Ctrl+Enter to seal and send
    act(() => {
      window.dispatchEvent(
        new KeyboardEvent("keydown", { key: "Enter", ctrlKey: true })
      );
    });
    expect(result.current.isSealing).toBe(true);
    act(() => {
      vi.advanceTimersByTime(250);
    });
    expect(onSeal).toHaveBeenCalled();
  });

  it("ignores keyboard shortcuts when typing in inputs", () => {
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, vi.fn(), vi.fn())
    );

    const input = document.createElement("input");
    document.body.appendChild(input);

    act(() => {
      const event = new KeyboardEvent("keydown", { key: "1" });
      Object.defineProperty(event, "target", { value: input });
      window.dispatchEvent(event);
    });

    expect(result.current.stage).toBe("reading");
    document.body.removeChild(input);
  });

  it("declines through the docket and through the 4 key", () => {
    const onDecline = vi.fn();
    const { result } = renderHook(() =>
      useLetterScene(DEFAULT_LETTER_SCENARIO, vi.fn(), vi.fn(), undefined, onDecline)
    );

    act(() => {
      result.current.handleSelectDocket("decline");
    });
    expect(onDecline).toHaveBeenCalledTimes(1);

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "4" }));
    });
    expect(onDecline).toHaveBeenCalledTimes(2);
  });

  it("ignores a decline when the letter cannot be declined", () => {
    const onDecline = vi.fn();
    const pkg = { ...DEFAULT_LETTER_SCENARIO, isDeclinable: false };
    const { result } = renderHook(() =>
      useLetterScene(pkg, vi.fn(), vi.fn(), undefined, onDecline)
    );

    act(() => {
      result.current.handleSelectDocket("decline");
    });

    expect(onDecline).not.toHaveBeenCalled();
  });
});
