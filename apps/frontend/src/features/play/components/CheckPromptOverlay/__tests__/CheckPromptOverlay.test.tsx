import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { usePlayStore } from "../../../stores/play.store";
import { CheckPromptOverlay } from "../CheckPromptOverlay";
import { CHECK_ROLL_ANIMATION_DURATION_MS } from "../../../constants/check.constants";

const mockSubmit = vi.fn();
const mockRevealAnimation = vi.fn();
vi.mock("../../../hooks/useCheckResolution", () => ({
  useCheckResolution: () => ({
    submit: mockSubmit,
    revealAnimation: mockRevealAnimation,
  }),
}));

function resetStore(): void {
  mockSubmit.mockClear();
  mockRevealAnimation.mockClear();
  usePlayStore.setState({
    active_check: null,
    is_narrating: false,
    is_check_animation_pending: false,
    resolved_check_outcome: null,
    streaming_text: "",
  });
}

describe("CheckPromptOverlay", () => {
  beforeEach(() => {
    resetStore();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders nothing when active_check is null", () => {
    const { container } = render(<CheckPromptOverlay />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the prompt with roll/decline buttons when idle", () => {
    usePlayStore.setState({
      active_check: {
        check_id: "check-1",
        check_type: "lockpicking",
        difficulty_class: 15,
        reasoning: "The mechanism is old and delicate.",
        resolved_roll: null,
      },
    });

    render(<CheckPromptOverlay />);

    expect(screen.getByText(/lockpicking check — DC 15/i)).toBeInTheDocument();
    expect(
      screen.getByText("The mechanism is old and delicate."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /roll/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /decline/i }),
    ).toBeInTheDocument();
  });

  it("submits an attempt resolution when Roll is clicked", () => {
    usePlayStore.setState({
      active_check: {
        check_id: "check-1",
        check_type: "lockpicking",
        difficulty_class: 15,
        resolved_roll: null,
      },
    });

    render(<CheckPromptOverlay />);
    fireEvent.click(screen.getByRole("button", { name: /roll/i }));

    expect(mockSubmit).toHaveBeenCalledWith({
      check_id: "check-1",
      resolution: "attempt",
    });
  });

  it("submits a decline resolution when Decline is clicked", () => {
    usePlayStore.setState({
      active_check: {
        check_id: "check-1",
        check_type: "lockpicking",
        difficulty_class: 15,
        resolved_roll: null,
      },
    });

    render(<CheckPromptOverlay />);
    fireEvent.click(screen.getByRole("button", { name: /decline/i }));

    expect(mockSubmit).toHaveBeenCalledWith({
      check_id: "check-1",
      resolution: "decline",
    });
  });

  it("shows the rolling animation while is_check_animation_pending is true", () => {
    usePlayStore.setState({
      active_check: {
        check_id: "check-1",
        check_type: "lockpicking",
        difficulty_class: 15,
        resolved_roll: null,
      },
      is_narrating: true,
      is_check_animation_pending: true,
    });

    render(<CheckPromptOverlay />);

    expect(screen.getByText(/rolling/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /roll/i })).not.toBeInTheDocument();
  });

  it("calls revealAnimation once the fixed duration elapses", () => {
    vi.useFakeTimers();
    usePlayStore.setState({
      active_check: {
        check_id: "check-1",
        check_type: "lockpicking",
        difficulty_class: 15,
        resolved_roll: null,
      },
      is_narrating: true,
      is_check_animation_pending: true,
    });

    render(<CheckPromptOverlay />);
    expect(mockRevealAnimation).not.toHaveBeenCalled();

    vi.advanceTimersByTime(CHECK_ROLL_ANIMATION_DURATION_MS);
    expect(mockRevealAnimation).toHaveBeenCalledTimes(1);
  });

  it("shows the resolved roll and streaming narration once revealed", () => {
    usePlayStore.setState({
      active_check: {
        check_id: "check-1",
        check_type: "lockpicking",
        difficulty_class: 15,
        resolved_roll: 17,
      },
      is_narrating: true,
      is_check_animation_pending: false,
      resolved_check_outcome: {
        check_id: "check-1",
        check_type: "lockpicking",
        difficulty_class: 15,
        resolved_roll: 17,
        is_success: true,
      },
      streaming_text: "Your fingers find the tumblers.",
    });

    render(<CheckPromptOverlay />);

    expect(screen.getByText(/rolled 17 vs dc 15/i)).toBeInTheDocument();
    expect(screen.getByText(/success/i)).toBeInTheDocument();
    expect(
      screen.getByText(/your fingers find the tumblers/i),
    ).toBeInTheDocument();
  });

  it("shows only streaming narration (no roll line) for a declined check", () => {
    usePlayStore.setState({
      active_check: {
        check_id: "check-1",
        check_type: "lockpicking",
        difficulty_class: 15,
        resolved_roll: null,
      },
      is_narrating: true,
      is_check_animation_pending: false,
      resolved_check_outcome: null,
      streaming_text: "You step back from the lock.",
    });

    render(<CheckPromptOverlay />);

    expect(screen.queryByText(/vs dc/i)).not.toBeInTheDocument();
    expect(
      screen.getByText(/you step back from the lock/i),
    ).toBeInTheDocument();
  });
});
