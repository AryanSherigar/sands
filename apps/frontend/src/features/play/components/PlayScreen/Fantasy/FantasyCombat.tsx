import type { ReturnTypeOfFantasyCombat } from "./FantasyCombat.types";

function eventText(event: NonNullable<ReturnTypeOfFantasyCombat["event"]>): string {
  if (event.immune) return "The attack had no effect.";
  if (event.hit) return `${event.damage} damage dealt.`;
  return "The attack missed.";
}

export function FantasyCombat({ combat, disabled }: { combat: ReturnTypeOfFantasyCombat; disabled: boolean }) {
  if (!combat.enabled) return null;
  const state = combat.combat;
  if (!state && !combat.encounters.length && !combat.isLoading && !combat.isLoadError && !combat.error) return null;
  const activeActor = state?.combatants.find((actor) => actor.actor_id === state.legal_actions[0]?.actor_id);
  return (
    <section aria-label="Combat" className="mb-6 w-full border border-border-strong bg-surface-raised p-4 text-content sm:p-5">
      <h2 className="font-display text-heading">Combat</h2>
      {combat.isLoading && <p className="mt-2 text-content-muted" role="status">Checking for encounters…</p>}
      {combat.isLoadError && <div role="alert" className="mt-3"><p>Could not load combat. Try again.</p><button type="button" className="mt-2 min-h-11 underline" onClick={() => void combat.refresh()}>Retry</button></div>}
      {!state && combat.encounters.length > 0 && <div className="mt-3 flex flex-wrap gap-3">{combat.encounters.map((encounter) => <button key={encounter.encounter_id} type="button" disabled={disabled || combat.isSubmitting || combat.error} onClick={() => combat.start(encounter.encounter_id)} className="min-h-11 border border-border-strong px-4 text-content hover:bg-hover-wash disabled:opacity-50">Start {encounter.title}</button>)}</div>}
      {state && <div className="mt-3 space-y-4">
        <p className="text-meta text-content-muted">Round {state.round_number}</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {state.combatants.map((actor) => <div key={actor.actor_id} className="border border-border-subtle p-3"><p className="font-semibold">{actor.side === "player" ? "You" : "Opponent"}</p><p className="mt-1 font-mono text-meta">Health {actor.health} / {actor.max_health}</p><div role="progressbar" aria-label={`${actor.side === "player" ? "Your" : "Opponent"} health`} aria-valuemin={0} aria-valuemax={actor.max_health} aria-valuenow={actor.health} className="mt-2 h-2 w-full bg-surface-inset"><div className="h-full bg-accent" style={{ width: `${(actor.health / actor.max_health) * 100}%` }} /></div></div>)}
        </div>
        <div aria-live="polite" className="text-body">
          {combat.event && <p>{eventText(combat.event)}</p>}
          {state.status === "active" && <p>{activeActor?.side === "player" ? "Your turn." : "Opponent’s turn."}</p>}
          {state.status === "player_defeated" && <p>You were defeated. Continue to see what happens.</p>}
          {state.status === "opponent_defeated" && <p>Opponent defeated.</p>}
        </div>
        {state.status === "active" && <button type="button" disabled={disabled || combat.isSubmitting || combat.error || !state.legal_actions.length} onClick={combat.attack} className="min-h-11 bg-primary px-5 font-semibold text-primary-contrast disabled:opacity-50">{activeActor?.side === "player" ? "Attack" : "Resolve opponent’s turn"}</button>}
        {state.status === "player_defeated" && !state.outcome_id && <button type="button" disabled={disabled || combat.isSubmitting || combat.error} onClick={combat.resolve} className="min-h-11 bg-primary px-5 font-semibold text-primary-contrast disabled:opacity-50">Continue</button>}
        {state.status === "opponent_defeated" && <button type="button" onClick={() => void combat.dismiss()} className="min-h-11 bg-primary px-5 font-semibold text-primary-contrast">Continue story</button>}
      </div>}
      {combat.error && <div role="alert" className="mt-4"><p>The action may not have saved. Retry or refresh combat.</p><div className="mt-2 flex gap-4"><button type="button" onClick={combat.retry} className="min-h-11 underline">Retry action</button><button type="button" onClick={() => void combat.refresh()} className="min-h-11 underline">Refresh combat</button></div></div>}
    </section>
  );
}
