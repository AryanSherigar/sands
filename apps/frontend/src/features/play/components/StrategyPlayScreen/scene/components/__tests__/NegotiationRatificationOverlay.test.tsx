import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NegotiationRatificationOverlay } from "../NegotiationRatificationOverlay";

describe("NegotiationRatificationOverlay", () => {
  it("renders agreed outcome with golden wax seal and handles close", () => {
    const handleClose = vi.fn();
    render(
      <NegotiationRatificationOverlay
        outcome={{ kind: "terms_card", result: "agreed" }}
        counterpartName="Queen Mira"
        onClose={handleClose}
      />
    );

    expect(screen.getByText("Treaty Sealed & Ratified")).toBeInTheDocument();
    expect(screen.getByText(/The sovereign pact with Queen Mira is sealed/i)).toBeInTheDocument();

    const returnBtn = screen.getByRole("button", { name: /return to campaign map/i });
    fireEvent.click(returnBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("renders refused / dissolved outcome with broken seal", () => {
    render(
      <NegotiationRatificationOverlay
        outcome={{ kind: "terms_card", result: "refused" }}
        counterpartName="Queen Mira"
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText("Talks Dissolved Without Agreement")).toBeInTheDocument();
  });
});
