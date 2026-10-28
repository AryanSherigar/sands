import { usePlayStore } from "../../stores/play.store";
import { MasterPlayScreen } from "./MasterPlayScreen";
import { NewbiePlayScreen } from "./NewbiePlayScreen";
import { StrategyPlayScreen } from "./StrategyPlayScreen";

export function PlayScreen() {
  const mode = usePlayStore((s) => s.playthrough?.mode) ?? "newbie";
  if (mode === "strategy") return <StrategyPlayScreen />;
  return mode === "master" ? <MasterPlayScreen /> : <NewbiePlayScreen />;
}
