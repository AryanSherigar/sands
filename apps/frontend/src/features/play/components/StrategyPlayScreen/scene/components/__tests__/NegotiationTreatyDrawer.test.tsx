import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NegotiationTreatyDrawer } from "../NegotiationTreatyDrawer";

describe("NegotiationTreatyDrawer", () => {
  it("renders pending clauses and handles signing", () => {
    const handleSign = vi.fn();
    const handleClose = vi.fn();

    render(
      <NegotiationTreatyDrawer
        isOpen={true}
        currentTurn={10}
        counterpartName="Queen Mira"
        proposal={{
          proposer_id: "mira",
          counterpart_id: "aldric",
          is_confirmed_by_counterpart: true,
          is_confirmed_by_player: false,
          terms: [
            {
              kind: "non_aggression",
              faction_a: "mira",
              faction_b: "aldric",
              duration_turns: 5,
            },
          ],
        }}
        onClose={handleClose}
        onSign={handleSign}
      />
    );

    expect(screen.getByText("On the Table")).toBeInTheDocument();
    expect(screen.getByText(/Non-Aggression Pact/i)).toBeInTheDocument();
    expect(screen.getByText(/5 turns/i)).toBeInTheDocument();

    const signBtn = screen.getByRole("button", { name: /sign the pact/i });
    fireEvent.click(signBtn);
    expect(handleSign).toHaveBeenCalledTimes(1);

    const closeBtn = screen.getByLabelText("Close drawer");
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("renders polymorphic treaty terms (peace, pay_gold, tribute, cede_region, release_prisoners, hostage)", () => {
    render(
      <NegotiationTreatyDrawer
        isOpen={true}
        currentTurn={10}
        counterpartName="Queen Mira"
        proposal={{
          proposer_id: "mira",
          counterpart_id: "aldric",
          is_confirmed_by_counterpart: true,
          is_confirmed_by_player: false,
          terms: [
            {
              kind: "peace",
              faction_a: "mira",
              faction_b: "aldric",
              tier: "short",
              duration_turns: 6,
              guarantor_ids: ["Dunmere League"],
            },
            {
              kind: "pay_gold",
              payer_id: "aldric",
              payee_id: "mira",
              amount: 200,
            },
            {
              kind: "tribute",
              payer_id: "aldric",
              payee_id: "mira",
              gold_per_turn: 30,
              duration_turns: 5,
            },
            {
              kind: "cede_region",
              from_faction_id: "aldric",
              to_faction_id: "mira",
              region_id: "reg-reach",
              region_name: "The Reach",
            },
            {
              kind: "release_prisoners",
              holder_id: "mira",
              recipient_id: "aldric",
              prisoner_ids: ["p1", "p2"],
              ransom_gold: 75,
            },
            {
              kind: "hostage",
              giver_id: "aldric",
              holder_id: "mira",
              leader_id: "prince-arthur",
              character_name: "Prince Arthur",
              duration_turns: 12,
            },
          ],
        }}
        onClose={vi.fn()}
        onSign={vi.fn()}
      />,
    );

    expect(screen.getByText("Peace Treaty")).toBeInTheDocument();
    expect(screen.getByText(/Short/i)).toBeInTheDocument();
    expect(screen.getByText(/Guarantors: Dunmere League/i)).toBeInTheDocument();

    expect(screen.getByText("Indemnity Payment")).toBeInTheDocument();
    expect(screen.getByText(/200g/i)).toBeInTheDocument();

    expect(screen.getByText("Annual Tribute")).toBeInTheDocument();
    expect(screen.getByText(/30g for 5 turns/i)).toBeInTheDocument();

    expect(screen.getByText("Ceded Territory")).toBeInTheDocument();
    expect(screen.getByText(/The Reach/i)).toBeInTheDocument();

    expect(screen.getByText("Release Prisoners")).toBeInTheDocument();
    expect(screen.getByText(/ransom of 75g/i)).toBeInTheDocument();

    expect(screen.getByText("Hostage Pledge")).toBeInTheDocument();
    expect(screen.getByText(/Prince Arthur/i)).toBeInTheDocument();
  });

  it("renders the multi-clause treaty kinds with their own labels", () => {
    render(
      <NegotiationTreatyDrawer
        isOpen={true}
        currentTurn={10}
        counterpartName="Queen Mira"
        proposal={{
          proposer_id: "aldric",
          counterpart_id: "mira",
          is_confirmed_by_counterpart: true,
          is_confirmed_by_player: false,
          terms: [
            { kind: "trade_deal", faction_a: "aldric", faction_b: "mira", duration_turns: 8 },
            { kind: "military_access", grantor_id: "mira", grantee_id: "aldric", duration_turns: 6 },
            {
              kind: "sworn_promise",
              promisor_id: "aldric",
              beneficiary_id: "mira",
              promise: "never_attack_faction",
              duration_turns: 10,
            },
            {
              kind: "alliance",
              faction_a: "aldric",
              faction_b: "mira",
              alliance_type: "defensive",
              duration_turns: 0,
            },
            {
              kind: "vassal",
              overlord_id: "mira",
              vassal_id: "aldric",
              tribute_share_percent: 20,
              duration_turns: 0,
            },
          ],
        }}
        onClose={vi.fn()}
        onSign={vi.fn()}
      />,
    );

    expect(screen.getByText("Trade Deal")).toBeInTheDocument();
    expect(screen.getByText(/8 turns \(ending turn 18\)/i)).toBeInTheDocument();
    expect(screen.getByText("Military Access")).toBeInTheDocument();
    expect(screen.getByText(/aldric may march through mira/i)).toBeInTheDocument();
    expect(screen.getByText("Sworn Promise")).toBeInTheDocument();
    expect(screen.getByText(/never to attack/i)).toBeInTheDocument();
    expect(screen.getByText("Alliance")).toBeInTheDocument();
    expect(screen.getByText("Vassalage")).toBeInTheDocument();
    expect(screen.getByText(/20% of income/i)).toBeInTheDocument();
    expect(screen.queryByText("Non-Aggression Pact")).not.toBeInTheDocument();
  });

  it("explains a conditional clause by its condition and mode", () => {
    render(
      <NegotiationTreatyDrawer
        isOpen={true}
        currentTurn={10}
        counterpartName="Queen Mira"
        proposal={{
          proposer_id: "aldric",
          counterpart_id: "mira",
          is_confirmed_by_counterpart: true,
          is_confirmed_by_player: false,
          terms: [
            {
              kind: "conditional",
              mode: "gate",
              when: { template: "treasury_above", faction_id: "aldric", value: 200 },
              expires_in_turns: 12,
              inner: { kind: "trade_deal", faction_a: "aldric", faction_b: "mira", duration_turns: 8 },
            },
          ],
        }}
        onClose={vi.fn()}
        onSign={vi.fn()}
      />,
    );

    expect(screen.getByText("If: Trade Deal")).toBeInTheDocument();
    expect(screen.getByText("Gated")).toBeInTheDocument();
    expect(screen.getByText(/Only while aldric's treasury rises above 200/i)).toBeInTheDocument();
    expect(screen.getByText(/Lapses after 12 turns/i)).toBeInTheDocument();
  });

  it("shows the engine verdict on the table", () => {
    const card = {
      proposer_id: "aldric",
      counterpart_id: "mira",
      is_confirmed_by_counterpart: true,
      is_confirmed_by_player: false,
      terms: [
        { kind: "non_aggression" as const, faction_a: "aldric", faction_b: "mira", duration_turns: 6 },
      ],
    };
    const { rerender } = render(
      <NegotiationTreatyDrawer
        isOpen={true}
        currentTurn={4}
        counterpartName="Queen Mira"
        proposal={card}
        verdict="accept"
        onClose={vi.fn()}
        onSign={vi.fn()}
      />,
    );
    expect(screen.getByText("Will sign")).toBeInTheDocument();

    rerender(
      <NegotiationTreatyDrawer
        isOpen={true}
        currentTurn={4}
        counterpartName="Queen Mira"
        proposal={null}
        verdict="haggle"
        onClose={vi.fn()}
        onSign={vi.fn()}
      />,
    );
    expect(screen.getByText("Will bargain")).toBeInTheDocument();
    expect(screen.getByText(/ease a demand/i)).toBeInTheDocument();

    rerender(
      <NegotiationTreatyDrawer
        isOpen={true}
        currentTurn={4}
        counterpartName="Queen Mira"
        proposal={null}
        verdict="refuse"
        onClose={vi.fn()}
        onSign={vi.fn()}
      />,
    );
    expect(screen.getByText("Refuses")).toBeInTheDocument();
  });

  it("shows how much each clause weighs in the deal", () => {
    render(
      <NegotiationTreatyDrawer
        isOpen={true}
        currentTurn={10}
        counterpartName="Queen Mira"
        clauseBands={["heavy", "light"]}
        proposal={{
          proposer_id: "mira",
          counterpart_id: "aldric",
          is_confirmed_by_counterpart: true,
          is_confirmed_by_player: false,
          terms: [
            { kind: "pay_gold", payer_id: "aldric", payee_id: "mira", amount: 90 },
            { kind: "non_aggression", faction_a: "mira", faction_b: "aldric", duration_turns: 4 },
          ],
        }}
        onClose={vi.fn()}
        onSign={vi.fn()}
      />,
    );

    expect(screen.getByText("Heavy weight")).toBeInTheDocument();
    expect(screen.getByText("Light weight")).toBeInTheDocument();
  });
});
