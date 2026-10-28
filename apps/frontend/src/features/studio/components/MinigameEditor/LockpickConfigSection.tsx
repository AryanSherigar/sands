import { Input } from "@/shared/components/ui/Input";
import { LockpickConfigSectionProps } from "./LockpickConfigSection.types";

const DIFFICULTY_LABELS: Record<number, string> = {
  1: "1 — Very Easy",
  2: "2 — Easy",
  3: "3 — Normal",
  4: "4 — Hard",
  5: "5 — Expert",
};

export function LockpickConfigSection({
  config,
  onChange,
}: LockpickConfigSectionProps) {
  const handleDifficulty = (event: React.ChangeEvent<HTMLInputElement>): void => {
    onChange({ ...config, difficulty: Number(event.target.value) });
  };

  const handlePicks = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const value = Math.max(1, Math.min(10, Number(event.target.value)));
    onChange({ ...config, picks: value });
  };

  const handleCopy =
    (field: keyof NonNullable<LockpickConfigSectionProps["config"]["copy"]>) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>): void => {
      onChange({
        ...config,
        copy: { ...config.copy, [field]: event.target.value } as NonNullable<
          LockpickConfigSectionProps["config"]["copy"]
        >,
      });
    };

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <label className="block text-sm font-medium text-zinc-200">
          Difficulty
          <span className="ml-2 font-normal text-zinc-400">
            {DIFFICULTY_LABELS[config.difficulty] ?? config.difficulty}
          </span>
        </label>
        <input
          type="range"
          min={1}
          max={5}
          step={1}
          value={config.difficulty}
          onChange={handleDifficulty}
          className="h-2 w-full cursor-pointer accent-amber-400"
        />
        <p className="text-xs text-zinc-500">
          Controls the sweet-spot arc width and oscillation speed. Higher = narrower arc, faster movement.
        </p>
      </div>

      <div className="space-y-1">
        <label className="block text-sm font-medium text-zinc-200">
          Starting picks
        </label>
        <input
          type="number"
          min={1}
          max={10}
          value={config.picks ?? 3}
          onChange={handlePicks}
          className="w-24 rounded border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm text-white focus:border-amber-400 focus:outline-hidden"
        />
        <p className="text-xs text-zinc-500">
          Each pick is one "health". Losing all picks = lose. Score on win = picks remaining.
        </p>
      </div>

      <div className="space-y-3">
        <p className="text-sm font-medium text-zinc-200">Copy (UI text)</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="space-y-1">
            <label className="text-xs text-zinc-400">Instructions</label>
            <Input
              value={config.copy?.instructions ?? ""}
              onChange={handleCopy("instructions")}
              placeholder="Align the pick with the sweet spot and hold."
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-zinc-400">Start button text</label>
            <Input
              value={config.copy?.start_text ?? ""}
              onChange={handleCopy("start_text")}
              placeholder="Begin"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-zinc-400">Win message</label>
            <Input
              value={config.copy?.win_text ?? ""}
              onChange={handleCopy("win_text")}
              placeholder="Unlocked!"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-zinc-400">Lose message</label>
            <Input
              value={config.copy?.lose_text ?? ""}
              onChange={handleCopy("lose_text")}
              placeholder="Pick broken."
            />
          </div>
        </div>
      </div>
    </div>
  );
}
