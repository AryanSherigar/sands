import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Input } from "../Input";
import { Card } from "../Card";
import { Badge } from "../Badge";
import { Modal } from "../Modal";
import { Toast } from "@/shared/components/feedback/Toast";

describe("Surface Primitives (Quiet Cinematic)", () => {
  it("renders Input with surface-inset, border-strong, and 6px radius", () => {
    render(<Input placeholder="Enter title" aria-label="Title" />);
    const input = screen.getByPlaceholderText("Enter title");
    expect(input.className).toContain("bg-surface-inset");
    expect(input.className).toContain("border-border-strong");
    expect(input.className).toContain("rounded-sm");
    expect(input.className).toContain("h-10");
  });

  it("renders Input with error state styling and message", () => {
    render(
      <Input
        placeholder="Email"
        aria-label="Email"
        error="Invalid email address"
      />,
    );
    const input = screen.getByPlaceholderText("Email");
    expect(input.className).toContain("border-danger");
    const errorText = screen.getByText("Invalid email address");
    expect(errorText.className).toContain("text-micro");
    expect(errorText.className).toContain("text-danger");
  });

  it("renders Card with surface-raised and 10px radius", () => {
    render(<Card>Card content</Card>);
    const card = screen.getByText("Card content");
    expect(card.className).toContain("bg-surface-raised");
    expect(card.className).toContain("border-border-subtle");
    expect(card.className).toContain("rounded-md");
  });

  it("renders Card with optional hover accent classes", () => {
    render(<Card hoverAccent>Hover Card</Card>);
    const card = screen.getByText("Hover Card");
    expect(card.className).toContain("hover:border-border-strong");
    expect(card.className).toContain("group-hover:border-t-2");
    expect(card.className).toContain("group-hover:border-t-(--accent)");
  });

  it("renders Badge with 6px radius and micro typography", () => {
    render(<Badge>Fantasy</Badge>);
    const badge = screen.getByText("Fantasy");
    expect(badge.className).toContain("rounded-sm");
    expect(badge.className).toContain("text-xs");
    expect(badge.className).toContain("gap-1.5");
  });

  it("renders Modal with 14px radius, border-strong, shadow-modal, and bg-black/75 backdrop", () => {
    render(
      <Modal isOpen onClose={vi.fn()} title="Test Modal">
        Modal body content
      </Modal>,
    );
    const dialog = screen.getByRole("dialog");
    expect(dialog.className).toContain("rounded-lg");
    expect(dialog.className).toContain("border-border-strong");
    expect(dialog.className).toContain("bg-surface-overlay");
    expect(dialog.className).toContain("shadow-modal");

    const backdrop = dialog.parentElement;
    expect(backdrop?.className).toContain("bg-black/75");
    expect(backdrop?.className).toContain("backdrop-blur-xs");
  });

  it("renders Toast with 10px radius, border-strong, shadow-float, and status styling", () => {
    render(
      <Toast
        message="Story published successfully"
        type="success"
        onClose={vi.fn()}
      />,
    );
    const toast = screen.getByRole("status");
    expect(toast.className).toContain("rounded-md");
    expect(toast.className).toContain("border-border-strong");
    expect(toast.className).toContain("bg-surface-overlay");
    expect(toast.className).toContain("shadow-float");
    expect(screen.getByText("Story published successfully")).toBeInTheDocument();
  });
});
