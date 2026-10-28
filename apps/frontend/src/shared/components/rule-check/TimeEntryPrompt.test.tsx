import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TimeEntryPrompt } from "./TimeEntryPrompt";
import { TimeEntryPromptProps } from "./TimeEntryPrompt.types";

const ENTER_LABEL = "Write it in the Log";
const REJECT_LABEL = "Reject the visitor";

const renderPrompt = (
  overrides: Partial<TimeEntryPromptProps> = {},
): TimeEntryPromptProps => {
  const props: TimeEntryPromptProps = {
    prompt: "A visitor signs in.",
    toldLabel: "11:52 PM",
    wallLabel: "11:40 PM",
    enterLabel: ENTER_LABEL,
    rejectLabel: REJECT_LABEL,
    remainingMs: 8200,
    windowMs: 12000,
    isSubmitting: false,
    onEnter: vi.fn(),
    onReject: vi.fn(),
    ...overrides,
  };
  render(<TimeEntryPrompt {...props} />);
  return props;
};

describe("TimeEntryPrompt", () => {
  it("shows the prompt, both times and focuses the input in a modal dialog", () => {
    renderPrompt();

    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("A visitor signs in.")).toBeInTheDocument();
    expect(screen.getByText("The visitor says")).toBeInTheDocument();
    expect(screen.getByText("11:52 PM")).toBeInTheDocument();
    expect(screen.getByText("The wall clock reads")).toBeInTheDocument();
    expect(screen.getByText("11:40 PM")).toBeInTheDocument();
    expect(screen.getByLabelText("Time for the Log")).toHaveFocus();
  });

  it("omits a row whose label is missing", () => {
    renderPrompt({ wallLabel: null });

    expect(screen.queryByText("The wall clock reads")).toBeNull();
    expect(screen.getByText("The visitor says")).toBeInTheDocument();
  });

  it("limits the input to 16 characters", () => {
    renderPrompt();

    expect(screen.getByLabelText("Time for the Log")).toHaveAttribute(
      "maxlength",
      "16",
    );
  });

  it("keeps the enter button disabled until the text reads as a time", async () => {
    renderPrompt();
    const user = userEvent.setup();
    const button = screen.getByRole("button", { name: ENTER_LABEL });

    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Time for the Log"), "eleven");
    expect(button).toBeDisabled();
    await user.clear(screen.getByLabelText("Time for the Log"));
    await user.type(screen.getByLabelText("Time for the Log"), "11:52 pm");
    expect(button).toBeEnabled();
  });

  it("reports the typed text on click and on Enter", async () => {
    const props = renderPrompt();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Time for the Log"), "23:52");
    await user.click(screen.getByRole("button", { name: ENTER_LABEL }));
    await user.type(screen.getByLabelText("Time for the Log"), "{Enter}");

    expect(props.onEnter).toHaveBeenCalledTimes(2);
    expect(props.onEnter).toHaveBeenCalledWith("23:52");
  });

  it("does not submit an invalid entry with Enter", async () => {
    const props = renderPrompt();

    await userEvent
      .setup()
      .type(screen.getByLabelText("Time for the Log"), "nope{Enter}");

    expect(props.onEnter).not.toHaveBeenCalled();
  });

  it("reports a rejection", async () => {
    const props = renderPrompt();

    await userEvent.setup().click(screen.getByRole("button", { name: REJECT_LABEL }));

    expect(props.onReject).toHaveBeenCalledTimes(1);
  });

  it("disables both buttons while submitting", () => {
    renderPrompt({ isSubmitting: true });

    expect(screen.getByRole("button", { name: ENTER_LABEL })).toBeDisabled();
    expect(screen.getByRole("button", { name: REJECT_LABEL })).toBeDisabled();
  });

  it("shows the countdown as whole seconds", () => {
    renderPrompt({ remainingMs: 8200 });

    expect(screen.getByText(/9 seconds remaining/i)).toHaveAttribute(
      "aria-live",
      "polite",
    );
  });
});
