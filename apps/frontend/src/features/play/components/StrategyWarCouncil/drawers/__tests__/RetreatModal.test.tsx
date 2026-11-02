import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RetreatModal } from "../RetreatModal";

describe("RetreatModal", () => {
  it("focuses the dialog, cancels on Escape and shows a withdrawal error", () => {
    const handleCancel = vi.fn();
    render(
      <RetreatModal
        isOpen
        isWithdrawing={false}
        errorMessage="Withdrawal is not available."
        onCancel={handleCancel}
        onConfirm={vi.fn()}
      />,
    );

    expect(screen.getByRole("alertdialog").contains(document.activeElement)).toBe(true);
    expect(screen.getByText("Withdrawal is not available.")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });

    expect(handleCancel).toHaveBeenCalledTimes(1);
  });

  it("ignores Escape while the withdrawal is being sent", () => {
    const handleCancel = vi.fn();
    render(<RetreatModal isOpen isWithdrawing onCancel={handleCancel} onConfirm={vi.fn()} />);

    fireEvent.keyDown(document, { key: "Escape" });

    expect(handleCancel).not.toHaveBeenCalled();
  });
});
