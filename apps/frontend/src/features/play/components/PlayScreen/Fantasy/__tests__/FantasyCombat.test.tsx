import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useFantasyCombat } from "../../../../hooks/useFantasyCombat";
import type { PlaythroughData } from "../../../../types/play.types";
import { FantasyCombat } from "../FantasyCombat";

const player = { actor_id: "hero", side: "player", health: 8, max_health: 20 };
const enemy = { actor_id: "foe", side: "opponent", health: 15, max_health: 15 };
const initial = { encounter_id: "ambush", revision: 0, round_number: 1, status: "active",
  outcome_id: null, combatants: [player, enemy], legal_actions: [{ actor_id: "hero", target_id: "foe", action_id: "attack" }] };
const playthrough = { playthrough_id: "p", participant_id: "owner", combat_enabled: true, is_spectator: false } as PlaythroughData;

function Harness() {
  const combat = useFantasyCombat(playthrough, false);
  return <><FantasyCombat combat={combat} disabled={false} /><p>{combat.isBlocked ? "Story blocked" : "Story available"}</p></>;
}

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><Harness /></QueryClientProvider>);
}

describe("fantasy combat", () => {
  it("starts an authored encounter and renders committed attack results", async () => {
    let action: Record<string, unknown> | null = null;
    server.use(
      http.get("*/v1/combat/p/options", () => HttpResponse.json({ state: null, encounters: [{ encounter_id: "ambush", title: "Ambush" }] })),
      http.post("*/v1/combat/start", () => HttpResponse.json(initial)),
      http.post("*/v1/combat/action", async ({ request }) => {
        action = await request.json() as Record<string, unknown>;
        return HttpResponse.json({ state: { ...initial, revision: 1, combatants: [player, { ...enemy, health: 10 }], legal_actions: [{ actor_id: "foe", target_id: "hero", action_id: "attack" }] }, event: { actor_id: "hero", target_id: "foe", hit: true, immune: false, damage: 5 } });
      }),
    );
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Start Ambush" }));
    expect(await screen.findByText("Health 8 / 20")).toBeInTheDocument();
    expect(screen.getByText("Story blocked")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Attack" }));
    expect(await screen.findByText("Health 10 / 15")).toBeInTheDocument();
    expect(screen.getByText("5 damage dealt.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resolve opponent’s turn" })).toBeEnabled();
    expect(action).toMatchObject({ action: { actor_id: "hero", target_id: "foe", expected_revision: 0 } });
  });

  it("retries a failed action with the same id and payload", async () => {
    const bodies: unknown[] = [];
    server.use(
      http.get("*/v1/combat/p/options", () => HttpResponse.json({ state: initial, encounters: [] })),
      http.post("*/v1/combat/action", async ({ request }) => {
        bodies.push(await request.json());
        if (bodies.length === 1) return new HttpResponse(null, { status: 503 });
        return HttpResponse.json({ state: { ...initial, revision: 1 }, event: { hit: false, immune: false, damage: 0 } });
      }),
    );
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Attack" }));
    fireEvent.click(await screen.findByRole("button", { name: "Retry action" }));
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[0]).toEqual(bodies[1]);
    expect(await screen.findByText("The attack missed.")).toBeInTheDocument();
  });

  it("resumes a defeated combat and applies the server outcome", async () => {
    let resolved = false;
    const defeated = { ...initial, revision: 2, status: "player_defeated", combatants: [{ ...player, health: 0 }, enemy], legal_actions: [] };
    server.use(
      http.get("*/v1/combat/p/options", () => HttpResponse.json({ state: resolved ? null : defeated, encounters: [] })),
      http.post("*/v1/combat/outcome", () => { resolved = true; return HttpResponse.json({ state: { ...defeated, outcome_id: "rescue", revision: 3 }, outcome_id: "rescue" }); }),
    );
    setup();
    expect(await screen.findByText("You were defeated. Continue to see what happens.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Story available")).toBeInTheDocument();
  });

  it("blocks story input when combat status cannot be loaded", async () => {
    server.use(http.get("*/v1/combat/p/options", () => new HttpResponse(null, { status: 503 })));
    setup();
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load combat");
    expect(screen.getByText("Story blocked")).toBeInTheDocument();
  });
});
