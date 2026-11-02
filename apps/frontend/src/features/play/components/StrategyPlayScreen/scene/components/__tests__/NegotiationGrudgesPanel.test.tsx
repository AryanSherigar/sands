import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NegotiationGrudgesPanel } from "../NegotiationGrudgesPanel";

describe("NegotiationGrudgesPanel", () => {
  it("renders nothing while the leader has voiced no grudge", () => {
    const { container } = render(<NegotiationGrudgesPanel grudges={[]} leaderName="Queen Mira" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("lists a voiced grudge with its strength in words", () => {
    render(
      <NegotiationGrudgesPanel
        leaderName="Queen Mira"
        grudges={[
          { text: "You broke the truce.", band: "burning", is_inherited: false, predecessor_name: null },
        ]}
      />,
    );
    expect(screen.getByRole("region", { name: /held against you/i })).toBeInTheDocument();
    expect(screen.getByText("You broke the truce.")).toBeInTheDocument();
    expect(screen.getByText(/burning/i)).toBeInTheDocument();
    expect(screen.queryByText(/inherited/i)).not.toBeInTheDocument();
  });

  it("names the predecessor when the grudge was inherited", () => {
    render(
      <NegotiationGrudgesPanel
        leaderName="Queen Mira"
        grudges={[
          { text: "You insulted them.", band: "faint", is_inherited: true, predecessor_name: "King Aldric" },
        ]}
      />,
    );
    expect(screen.getByText(/inherited from King Aldric/i)).toBeInTheDocument();
  });

  it("falls back to a generic label when the predecessor is unknown", () => {
    render(
      <NegotiationGrudgesPanel
        leaderName="Queen Mira"
        grudges={[
          { text: "You insulted them.", band: "firm", is_inherited: true, predecessor_name: null },
        ]}
      />,
    );
    expect(screen.getByText(/inherited from a predecessor/i)).toBeInTheDocument();
  });
});
