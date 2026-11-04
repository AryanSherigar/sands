import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EmailSignInForm } from "../EmailSignInForm";

describe("EmailSignInForm", () => {
  it("submits the typed email and password", async () => {
    const onSubmit = vi.fn().mockResolvedValue(true);
    render(<EmailSignInForm onSubmit={onSubmit} isPending={false} />);
    await userEvent.type(screen.getByLabelText("Email"), "judge@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "secret");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(onSubmit).toHaveBeenCalledWith("judge@example.com", "secret");
  });

  it("does not submit while a sign-in is pending", async () => {
    const onSubmit = vi.fn();
    render(<EmailSignInForm onSubmit={onSubmit} isPending />);
    expect(screen.getByRole("button", { name: "Signing in…" })).toBeDisabled();
  });

  it("does not submit with an empty form", async () => {
    const onSubmit = vi.fn();
    render(<EmailSignInForm onSubmit={onSubmit} isPending={false} />);
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
