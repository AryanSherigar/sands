import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GrantConsentForm } from "../GrantConsentForm";

const TARGETS = [
  { id: "car", label: "House Carrow" },
  { id: "dun", label: "House Dunwick" },
];

describe("GrantConsentForm", () => {
  it("builds a consent order for the chosen realm and action", () => {
    const onSubmit = vi.fn();
    render(<GrantConsentForm factionId="me" vassalageId="v1" targets={TARGETS} onSubmit={onSubmit} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Who"), { target: { value: "dun" } });
    fireEvent.change(screen.getByLabelText("What your vassal may do"), { target: { value: "pact" } });
    fireEvent.click(screen.getByRole("button", { name: "Grant consent" }));

    expect(onSubmit).toHaveBeenCalledWith({
      kind: "grant_consent",
      faction_id: "me",
      vassalage_id: "v1",
      action: "pact",
      target_faction_id: "dun",
    });
  });

  it("cannot be sent when there is no one to name", () => {
    render(<GrantConsentForm factionId="me" vassalageId="v1" targets={[]} onSubmit={vi.fn()} onCancel={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Grant consent" })).toBeDisabled();
  });
});
