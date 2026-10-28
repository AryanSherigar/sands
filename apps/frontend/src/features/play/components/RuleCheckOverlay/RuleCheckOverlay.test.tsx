import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { usePlayStore } from "../../stores/play.store";
import { PlaythroughData } from "../../types/play.types";
import { RuleCheckOverlay } from "./RuleCheckOverlay";

let capturedBody: Record<string, unknown> | null = null;

vi.mock("@/shared/lib/sse-client", () => ({
  createPostSSEConnection: (_url: string, body: Record<string, unknown>) => {
    capturedBody = body;
    return vi.fn();
  },
}));

vi.mock("@/shared/api/playthroughs.api", () => ({ getPlaythrough: vi.fn() }));

const armRuleCheckMock = vi.hoisted(() => vi.fn());
vi.mock("../../api/ruleCheck.api", () => ({ armRuleCheck: armRuleCheckMock }));

const playthrough = {
  playthrough_id: "pt-1",
  participant_id: "participant-1",
  turns: [{ narration_text: "The lamp gutters and the phone rings." }],
};

const openPrompt = (initialRemainingMs = 12000, isArmed = true): void => {
  usePlayStore.setState({
    playthrough: playthrough as PlaythroughData,
    is_rule_check_submitting: false,
    active_rule_check: {
      check_id: "chk-1",
      kind: "timed_choice",
      prompt: "The phone rings.",
      options: [
        { id: "answer", label: "Answer it" },
        { id: "ignore", label: "Let it ring" },
      ],
      window_ms: 12000,
      issued_at: 0,
      is_armed: isArmed,
      initial_remaining_ms: initialRemainingMs,
      started_at_client_ms: Date.now(),
    },
  });
};

describe("RuleCheckOverlay", () => {
  beforeEach(() => {
    capturedBody = null;
    armRuleCheckMock.mockReset();
    usePlayStore.setState({ active_rule_check: null, playthrough: null });
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders nothing when no prompt is open", () => {
    render(<RuleCheckOverlay />);

    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows the open prompt from the store", () => {
    openPrompt();

    render(<RuleCheckOverlay />);

    expect(screen.getByText("The phone rings.")).toBeInTheDocument();
  });

  it("posts the chosen option as a check report", async () => {
    openPrompt();
    render(<RuleCheckOverlay />);

    await userEvent.setup().click(screen.getByRole("button", { name: "Answer it" }));

    expect(capturedBody).toMatchObject({
      action_kind: "check_report",
      check_report: { check_id: "chk-1", choice_id: "answer" },
    });
  });

  it("reports a timeout when the countdown reaches zero", () => {
    vi.useFakeTimers();
    openPrompt(1000);
    render(<RuleCheckOverlay />);

    act(() => {
      vi.advanceTimersByTime(1500);
    });

    expect(capturedBody).toMatchObject({
      action_kind: "check_report",
      check_report: { check_id: "chk-1", timed_out: true },
    });
  });

  it("does not report a timeout twice", () => {
    vi.useFakeTimers();
    openPrompt(500);
    render(<RuleCheckOverlay />);

    act(() => {
      vi.advanceTimersByTime(1500);
    });
    const firstBody = capturedBody;
    capturedBody = null;
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(firstBody).not.toBeNull();
    expect(capturedBody).toBeNull();
  });

  describe("before the clock is armed", () => {
    it("locks the prompt and starts no countdown", () => {
      vi.useFakeTimers();
      armRuleCheckMock.mockReturnValue(new Promise(() => undefined));
      openPrompt(12000, false);
      render(<RuleCheckOverlay />);

      act(() => {
        vi.advanceTimersByTime(1000);
      });

      expect(screen.getByText("Read on\u2026")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Answer it" })).toBeDisabled();
      expect(capturedBody).toBeNull();
    });

    it("never reports a timeout while locked", () => {
      vi.useFakeTimers();
      armRuleCheckMock.mockReturnValue(new Promise(() => undefined));
      openPrompt(500, false);
      render(<RuleCheckOverlay />);

      act(() => {
        vi.advanceTimersByTime(1500);
      });

      expect(capturedBody).toBeNull();
    });

    it("arms after a reading beat, then unlocks with the server's window", async () => {
      vi.useFakeTimers();
      armRuleCheckMock.mockResolvedValue({
        check_id: "chk-1",
        issued_at: 1_000,
        window_ms: 12000,
        server_time_ms: 1_000,
      });
      openPrompt(12000, false);
      render(<RuleCheckOverlay />);

      expect(armRuleCheckMock).not.toHaveBeenCalled();
      await act(async () => {
        await vi.advanceTimersByTimeAsync(2100);
      });

      expect(armRuleCheckMock).toHaveBeenCalledWith({
        playthrough_id: "pt-1",
        participant_id: "participant-1",
        check_id: "chk-1",
      });
      expect(screen.getByRole("button", { name: "Answer it" })).toBeEnabled();
      expect(screen.getByText(/seconds? remaining/)).toBeInTheDocument();
    });

    it("retries when arming fails", async () => {
      vi.useFakeTimers();
      armRuleCheckMock
        .mockRejectedValueOnce(new Error("offline"))
        .mockResolvedValue({
          check_id: "chk-1",
          issued_at: 1_000,
          window_ms: 12000,
          server_time_ms: 1_000,
        });
      openPrompt(12000, false);
      render(<RuleCheckOverlay />);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(3500);
      });

      expect(armRuleCheckMock).toHaveBeenCalledTimes(2);
      expect(screen.getByRole("button", { name: "Answer it" })).toBeEnabled();
    });
  });

  it("is not shown to spectators", () => {
    openPrompt();
    usePlayStore.setState({
      playthrough: { ...playthrough, is_spectator: true } as PlaythroughData,
    });

    render(<RuleCheckOverlay />);

    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("flags a report as hidden once the tab stayed away past the grace", async () => {
    vi.useFakeTimers();
    openPrompt();
    render(<RuleCheckOverlay />);
    const visibility = vi.spyOn(document, "hidden", "get");

    act(() => {
      visibility.mockReturnValue(true);
      document.dispatchEvent(new Event("visibilitychange"));
      vi.advanceTimersByTime(1600);
    });
    act(() => {
      screen.getByRole("button", { name: "Answer it" }).click();
    });

    expect(capturedBody).toMatchObject({
      check_report: { choice_id: "answer", was_hidden: true },
    });
    visibility.mockRestore();
  });

  it("forgives a quick glance away shorter than the grace", () => {
    vi.useFakeTimers();
    openPrompt();
    render(<RuleCheckOverlay />);
    const visibility = vi.spyOn(document, "hidden", "get");

    act(() => {
      visibility.mockReturnValue(true);
      document.dispatchEvent(new Event("visibilitychange"));
      vi.advanceTimersByTime(500);
      visibility.mockReturnValue(false);
      document.dispatchEvent(new Event("visibilitychange"));
      vi.advanceTimersByTime(2000);
    });
    act(() => {
      screen.getByRole("button", { name: "Answer it" }).click();
    });

    expect(capturedBody).toMatchObject({
      check_report: { check_id: "chk-1", choice_id: "answer" },
    });
    expect(
      (capturedBody as { check_report: Record<string, unknown> }).check_report,
    ).not.toHaveProperty("was_hidden");
    visibility.mockRestore();
  });

  it("is untimed with reduced effects: no countdown, no timeout report, flagged", async () => {
    vi.useFakeTimers();
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    openPrompt(1000);
    render(<RuleCheckOverlay />);

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.getByText("Take your time")).toBeInTheDocument();
    expect(capturedBody).toBeNull();
    act(() => {
      screen.getByRole("button", { name: "Answer it" }).click();
    });
    expect(capturedBody).toMatchObject({
      check_report: { choice_id: "answer", is_untimed: true },
    });
  });

  it("never reports the hidden tab in untimed mode", () => {
    vi.useFakeTimers();
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    openPrompt();
    render(<RuleCheckOverlay />);
    const visibility = vi.spyOn(document, "hidden", "get");

    act(() => {
      visibility.mockReturnValue(true);
      document.dispatchEvent(new Event("visibilitychange"));
      vi.advanceTimersByTime(5000);
    });
    act(() => {
      screen.getByRole("button", { name: "Answer it" }).click();
    });

    expect(
      (capturedBody as { check_report: Record<string, unknown> }).check_report,
    ).not.toHaveProperty("was_hidden");
    visibility.mockRestore();
  });

  it("shows recall variants and reports the chosen variant id", async () => {
    usePlayStore.setState({
      playthrough: playthrough as PlaythroughData,
      is_rule_check_submitting: false,
      active_rule_check: {
        check_id: "chk-2",
        kind: "recall",
        prompt: "Which wording was the original rule?",
        options: [],
        variants: [
          { id: "v1", text: "Always answer" },
          { id: "v0", text: "Never answer" },
        ],
        window_ms: 30000,
        issued_at: 0,
        initial_remaining_ms: 30000,
        started_at_client_ms: Date.now(),
      },
    });
    render(<RuleCheckOverlay />);

    await userEvent
      .setup()
      .click(screen.getByRole("radio", { name: /Never answer/ }));

    expect(capturedBody).toMatchObject({
      action_kind: "check_report",
      check_report: { check_id: "chk-2", choice_id: "v0" },
    });
  });

  describe("time_entry", () => {
    const openTimeEntry = (): void => {
      usePlayStore.setState({
        playthrough: playthrough as PlaythroughData,
        is_rule_check_submitting: false,
        active_rule_check: {
          check_id: "chk-3",
          kind: "time_entry",
          prompt: "A visitor signs in.",
          options: [
            { id: "enter", label: "Write it in the Log" },
            { id: "reject", label: "Reject the visitor" },
          ],
          told_label: "11:52 PM",
          wall_label: "11:40 PM",
          wall_minute_of_day: 1420,
          window_ms: 20000,
          issued_at: 0,
          initial_remaining_ms: 20000,
          started_at_client_ms: Date.now(),
        },
      });
    };

    it("shows both the told time and the wall clock", () => {
      openTimeEntry();

      render(<RuleCheckOverlay />);

      expect(screen.getByText("The visitor says")).toBeInTheDocument();
      expect(screen.getByText("11:52 PM")).toBeInTheDocument();
      expect(screen.getByText("The wall clock reads")).toBeInTheDocument();
      expect(screen.getByText("11:40 PM")).toBeInTheDocument();
    });

    it("reports the typed time as an enter choice", async () => {
      openTimeEntry();
      render(<RuleCheckOverlay />);
      const user = userEvent.setup();

      await user.type(screen.getByLabelText("Time for the Log"), "11:52 pm");
      await user.click(screen.getByRole("button", { name: "Write it in the Log" }));

      expect(capturedBody).toMatchObject({
        action_kind: "check_report",
        check_report: {
          check_id: "chk-3",
          choice_id: "enter",
          entry_text: "11:52 pm",
        },
      });
    });

    it("reports a rejection without any entry text", async () => {
      openTimeEntry();
      render(<RuleCheckOverlay />);

      await userEvent
        .setup()
        .click(screen.getByRole("button", { name: "Reject the visitor" }));

      const report = (capturedBody as { check_report: Record<string, unknown> })
        .check_report;
      expect(report).toMatchObject({ check_id: "chk-3", choice_id: "reject" });
      expect(report).not.toHaveProperty("entry_text");
    });

    it("reports a timeout when the countdown reaches zero", () => {
      vi.useFakeTimers();
      openTimeEntry();
      usePlayStore.setState((state) => ({
        active_rule_check: state.active_rule_check && {
          ...state.active_rule_check,
          initial_remaining_ms: 1000,
        },
      }));
      render(<RuleCheckOverlay />);

      act(() => {
        vi.advanceTimersByTime(1500);
      });

      expect(capturedBody).toMatchObject({
        check_report: { check_id: "chk-3", timed_out: true },
      });
    });
  });
});
