import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Modal } from "../Modal";

const renderModal = (props: Partial<React.ComponentProps<typeof Modal>> = {}) => {
  const onClose = vi.fn();
  render(
    <Modal isOpen onClose={onClose} title="Sign in" {...props}>
      <button>First</button>
      <button>Last</button>
    </Modal>,
  );
  return onClose;
};

describe("Modal", () => {
  it("closes on Escape by default", async () => {
    const onClose = renderModal();
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("ignores Escape, backdrop clicks and hides the close button when not dismissible", async () => {
    const onClose = renderModal({ isDismissible: false });
    await userEvent.keyboard("{Escape}");
    await userEvent.click(screen.getByRole("dialog").parentElement as HTMLElement);
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Close" })).toBeNull();
  });

  it("moves focus into the dialog and traps Tab", async () => {
    renderModal();
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "First" })).toHaveFocus();
    await userEvent.tab();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();
    await userEvent.tab({ shift: true });
    expect(screen.getByRole("button", { name: "Last" })).toHaveFocus();
  });

  it("restores focus to the opener when it closes", () => {
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();
    const { rerender } = render(
      <Modal isOpen onClose={vi.fn()} title="T">
        <button>Inside</button>
      </Modal>,
    );
    rerender(
      <Modal isOpen={false} onClose={vi.fn()} title="T">
        <button>Inside</button>
      </Modal>,
    );
    expect(opener).toHaveFocus();
    opener.remove();
  });
});
