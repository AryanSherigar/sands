import { usePlayStore } from "../../stores/play.store";
import { MasterPlayScreen } from "./MasterPlayScreen";
import { NewbiePlayScreen } from "./NewbiePlayScreen";
import { StrategyPlayScreen } from "./StrategyPlayScreen";
import { FantasyPlayScreen } from "./Fantasy/FantasyPlayScreen";

export function PlayScreen({ scenarioSnapshot, state }: { scenarioSnapshot?: Record<string, unknown>; state?: Record<string, unknown> } = {}) {
  const mode = usePlayStore((s) => s.playthrough?.mode) ?? "newbie";
  const primaryGenre = usePlayStore((s) => s.playthrough?.genre_tags?.[0]);
  if (mode === "strategy") return <StrategyPlayScreen />;
  if (primaryGenre === "High Fantasy") return <FantasyPlayScreen scenarioSnapshot={scenarioSnapshot} mapState={state} />;
  return mode === "master" ? <MasterPlayScreen /> : <NewbiePlayScreen />;
}
