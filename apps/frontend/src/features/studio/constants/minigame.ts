export const MINIGAME_TYPE_OPTIONS = [
  { value: "dodge", label: "Built-in: Ashfall Dodge" },
  { value: "lockpick", label: "Built-in: Lockpick" },
  { value: "rhythm_composure", label: "Composure (rhythm)" },
] as const;

export const OUTCOME_MODE_OPTIONS = [
  { value: "binary", label: "Binary (win / lose)" },
  { value: "tiered", label: "Tiered (score ranges)" },
] as const;
