import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RuleCheckPrompt } from "./RuleCheckPrompt";
import { RuleCheckPromptProps } from "./RuleCheckPrompt.types";

const renderPrompt = (
  overrides: Partial<RuleCheckPromptProps> = {},
): RuleCheckPromptProps => {
  const props: RuleCheckPromptProps = {
    prompt: "The phone rings.",
    options: [
      { id: "answer", label: "Answer it" },
      { id: "ignore", label: "Let it ring" },
    ],
    remainingMs: 8200,
    windowMs: 12000,
    isSubmitting: false,
    onChoose: vi.fn(),
    ...overrides,
  };
  render(<RuleCheckPrompt {...props} />);
  return props;
};

describe("RuleCheckPrompt", () => {
  it("shows the prompt and one button per option inside a modal dialog", () => {
    renderPrompt();

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("The phone rings.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Answer it" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Let it ring" })).toBeInTheDocument();
  });

  it("reports the chosen option id", async () => {
    const props = renderPrompt();

    await userEvent.setup().click(screen.getByRole("button", { name: "Let it ring" }));

    expect(props.onChoose).toHaveBeenCalledWith("ignore");
  });

  it("shows the time left as a progress bar and whole seconds", () => {
    renderPrompt({ remainingMs: 8200, windowMs: 12000 });

    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuemax", "12000");
    expect(bar).toHaveAttribute("aria-valuenow", "8200");
    expect(screen.getByText(/9 seconds remaining/i)).toBeInTheDocument();
  });

  it("announces the remaining seconds politely, never assertively", () => {
    renderPrompt();

    const status = screen.getByText(/seconds remaining/i);
    expect(status).toHaveAttribute("aria-live", "polite");
  });

  it("says 1 second in the singular", () => {
    renderPrompt({ remainingMs: 400 });

    expect(screen.getByText(/1 second remaining/i)).toBeInTheDocument();
  });

  it("disables the options while an answer is being sent", () => {
    renderPrompt({ isSubmitting: true });

    for (const button of screen.getAllByRole("button")) {
      expect(button).toBeDisabled();
    }
  });

  it("focuses the first option when it opens", () => {
    renderPrompt();

    expect(screen.getByRole("button", { name: "Answer it" })).toHaveFocus();
  });

  it("keeps focus inside the dialog when tabbing past the last option", async () => {
    renderPrompt();
    const user = userEvent.setup();

    await user.tab();
    expect(screen.getByRole("button", { name: "Let it ring" })).toHaveFocus();
    await user.tab();

    expect(screen.getByRole("button", { name: "Answer it" })).toHaveFocus();
  });

  it("keeps focus inside the dialog when shift-tabbing before the first option", async () => {
    renderPrompt();

    await userEvent.setup().tab({ shift: true });

    expect(screen.getByRole("button", { name: "Let it ring" })).toHaveFocus();
  });

  it("does nothing on Escape, because a closed prompt is not a choice", async () => {
    const props = renderPrompt();

    await userEvent.setup().keyboard("{Escape}");

    expect(props.onChoose).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("replaces the countdown with a calm line when untimed", () => {
    renderPrompt({ isUntimed: true });

    expect(screen.getByText("Take your time")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.queryByText(/seconds? remaining/i)).toBeNull();
  });

  it("renders recall variants as a radio group of quoted wordings", async () => {
    const props = renderPrompt({
      isRecall: true,
      options: [
        { id: "v1", label: "Always answer" },
        { id: "v0", label: "Never answer" },
      ],
    });

    expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    await userEvent
      .setup()
      .click(screen.getByRole("radio", { name: /Never answer/ }));

    expect(props.onChoose).toHaveBeenCalledWith("v0");
  });

  it("does not use radio semantics for a timed choice", () => {
    renderPrompt();

    expect(screen.queryByRole("radiogroup")).toBeNull();
  });
});
