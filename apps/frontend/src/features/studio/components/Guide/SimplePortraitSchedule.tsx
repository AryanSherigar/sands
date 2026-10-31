import { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { useGuide } from "../../hooks/useGuide";
import type { EntityResponse } from "../../types/entity.types";

interface Cue { turn: number; character_ids: string[] }

export function SimplePortraitSchedule({ characters }: { characters: EntityResponse[] }) {
  const { scenario, saveFields } = useGuide();
  const [turn, setTurn] = useState(1);
  const [selected, setSelected] = useState<string[]>([]);
  if (!scenario || scenario.mode !== "newbie" || scenario.genre_tags?.[0] !== "Slice of Life") return null;
  const available = characters.filter((character) => character.avatar_url);
  if (!available.length) return null;
  const raw = scenario.rules?.portrait_schedule;
  const cues: Cue[] = Array.isArray(raw) ? raw.filter((item): item is Cue => item && typeof item === "object" && Number.isInteger(item.turn) && Array.isArray(item.character_ids)) : [];
  const write = (next: Cue[]) => saveFields({ rules: { ...scenario.rules, portrait_schedule: next } });
  const save = () => {
    if (!Number.isInteger(turn) || turn < 1) return;
    write([...cues.filter((cue) => cue.turn !== turn), { turn, character_ids: selected }].sort((left, right) => left.turn - right.turn));
  };
  return <fieldset className="space-y-2 border-t border-border-subtle pt-4">
    <legend className="font-medium text-content">Change portraits after a turn</legend>
    <p className="text-meta text-content-muted">Schedule scene changes by story turn. Leave all characters unchecked to clear the portraits.</p>
    <label className="block text-sm text-content">After turn <input type="number" min={1} value={turn} onChange={(event) => setTurn(Number(event.target.value))} className="ml-2 w-20 rounded border border-border-subtle bg-surface px-2 py-1" /></label>
    {available.map((character) => <label key={character.entity_id} className="flex items-center gap-2 text-sm text-content">
      <input type="checkbox" checked={selected.includes(character.entity_id)} disabled={!selected.includes(character.entity_id) && selected.length >= 2} onChange={(event) => setSelected(event.target.checked ? [...selected, character.entity_id] : selected.filter((id) => id !== character.entity_id))} />{character.canonical_name}
    </label>)}
    <Button type="button" variant="secondary" size="sm" disabled={!Number.isInteger(turn) || turn < 1} onClick={save}>Save scene change</Button>
    {cues.map((cue) => <div key={cue.turn} className="flex items-center gap-2 text-meta text-content-muted">After turn {cue.turn}: {cue.character_ids.map((id) => available.find((character) => character.entity_id === id)?.canonical_name ?? "Unavailable character").join(", ") || "No portraits"}<Button type="button" variant="ghost" size="sm" onClick={() => write(cues.filter((item) => item.turn !== cue.turn))} aria-label={`Remove scene change after turn ${cue.turn}`}>Remove</Button></div>)}
  </fieldset>;
}
