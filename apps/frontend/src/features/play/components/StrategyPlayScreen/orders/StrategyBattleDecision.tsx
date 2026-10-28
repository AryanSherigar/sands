import { useBattleControl } from "../../../hooks/useBattleControl";
import type { StrategyBattleDecisionProps } from "./StrategyBattleDecision.types";

export function StrategyBattleDecision({ playthroughId, world, regionNames }: StrategyBattleDecisionProps) {
  const { choose, isPending, errorInfo } = useBattleControl(playthroughId);
  const hasCommand = world.battles.some((battle) => battle.control_mode === "player" && (battle.current_turn ?? world.turn) === world.turn);
  const battles = world.battles.filter((battle) => battle.is_big && battle.control_mode === "undecided" && battle.status !== "resolved");
  return (
    <section aria-label="Battle command decision" aria-busy={isPending} className="absolute inset-x-4 bottom-28 z-40 mx-auto max-h-[60vh] max-w-lg overflow-y-auto rounded-xl bg-[#F7F0DC] p-5 text-[#3A3128] shadow-lg">
      <h2 className="font-serif text-2xl">Your armies await orders</h2>
      <p className="mt-2 text-sm">Take command of one battle this turn, or let your commanders follow their standing plans. No fighting begins until you choose.</p>
      {battles.map((battle) => (
        <div key={battle.id} className="mt-4 border-t border-[#3A3128]/20 pt-3">
          <h3 className="break-words font-semibold">{regionNames[battle.region_id] ?? battle.region_id}</h3>
          <div className="mt-3 flex flex-wrap gap-3">
            <button type="button" disabled={isPending || hasCommand} onClick={() => choose({ kind: "take_command", faction_id: world.my_faction.id, battle_id: battle.id })} className="rounded-md bg-[#46606E] px-4 py-2 text-white hover:bg-[#354F5A] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50">Take command</button>
            <button type="button" disabled={isPending} onClick={() => choose({ kind: "delegate_battle", faction_id: world.my_faction.id, battle_id: battle.id })} className="rounded-md border border-[#46606E] px-4 py-2 hover:bg-[#E8DEC6] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50">Delegate and continue</button>
          </div>
        </div>
      ))}
      {errorInfo && <p role="alert" className="mt-4 text-sm text-[#A8483E]">{errorInfo.message}</p>}
    </section>
  );
}
