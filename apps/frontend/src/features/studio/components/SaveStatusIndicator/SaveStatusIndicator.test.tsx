import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SaveStatusIndicator } from "./SaveStatusIndicator";

describe("SaveStatusIndicator", () => {
  it("shows Saving while a save is in flight", () => {
    render(<SaveStatusIndicator isSaving lastSaved={null} />);

    expect(screen.getByText("Saving…")).toBeInTheDocument();
  });

  it("shows Saved after a successful save", () => {
    render(<SaveStatusIndicator isSaving={false} lastSaved={new Date()} />);

    expect(screen.getByText("Saved")).toBeInTheDocument();
  });

  it("offers Retry when the last save failed", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(
      <SaveStatusIndicator
        isSaving={false}
        lastSaved={null}
        hasError
        onRetry={onRetry}
      />,
    );

    expect(screen.getByText(/couldn't save/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("keeps working for callers that pass no error props", () => {
    render(<SaveStatusIndicator isSaving={false} lastSaved={null} />);

    expect(screen.getByText("All changes saved")).toBeInTheDocument();
  });
});
