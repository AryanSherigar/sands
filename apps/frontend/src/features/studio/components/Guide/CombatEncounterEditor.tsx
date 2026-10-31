import { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { generateClientActionId } from "@/shared/lib/request-id";
import { useGuide } from "../../hooks/useGuide";
import { useEndConditions } from "../../hooks/useEndConditions";
import { useEntities } from "../../hooks/useEntities";
import { useMaps } from "../../hooks/useMaps";
import { useValueOptions } from "../../hooks/useValueOptions";
import { buildCombatTemplate, EMPTY_ACTOR, readCombatDraft } from "../../lib/combatTemplate";
import type { CombatActorDraft, CombatDraft } from "../../lib/combatTemplate";
const ACTOR_FIELDS: {
    key: keyof CombatActorDraft;
    label: string;
}[] = [
    { key: "health", label: "Starting health" }, { key: "max_health", label: "Maximum health" },
    { key: "attack", label: "Attack" }, { key: "armor", label: "Armor" },
    { key: "speed", label: "Speed" }, { key: "accuracy", label: "Accuracy (0–100)" },
    { key: "luck", label: "Luck (0–100)" },
];
const emptyDraft = (): CombatDraft => ({ title: "", trigger: "", player: { ...EMPTY_ACTOR }, opponent: { ...EMPTY_ACTOR }, recoveryHealth: "", recoveryLocationId: "", playerAttackTag: "", opponentRequiredTag: "", outcomeKind: "recover", endingId: "" });
export function CombatEncounterEditor() {
    const { scenario, scenarioId, saveFields } = useGuide();
    const { endConditions } = useEndConditions(scenario?.genre_tags?.[0] === "High Fantasy" ? scenarioId : null);
    const { entities } = useEntities(scenario?.genre_tags?.[0] === "High Fantasy" ? scenarioId : null);
    const { maps } = useMaps(scenario?.genre_tags?.[0] === "High Fantasy" ? scenarioId : null);
    const options = useValueOptions().filter((option) => option.kind === "boolean");
    const [isOpen, setOpen] = useState(false);
    const [draft, setDraft] = useState<CombatDraft>(emptyDraft);
    const [error, setError] = useState("");
    const [editingIndex, setEditingIndex] = useState<number | null>(null);
    const rules = scenario?.rules ?? {};
    const existing = rules.fantasy_combat;
    const config = existing && typeof existing === "object" && !Array.isArray(existing) ? existing as Record<string, unknown> : null;
    const encounters = Array.isArray(config?.encounters) ? config.encounters : [];
    const existingHealth = scenario?.state_schema?.player?.fields?.health?.initial;
    if (scenario && scenario.genre_tags?.[0] !== "High Fantasy")
        return null;
    const updateActor = (side: "player" | "opponent", key: keyof CombatActorDraft, value: string) => setDraft((current) => ({ ...current, [side]: { ...current[side], [key]: value } }));
    const save = (event: React.FormEvent) => {
        event.preventDefault();
        try {
            if (!scenario || !options.some((option) => option.path === draft.trigger))
                throw new Error("Choose an existing yes/no value as the trigger.");
            if (draft.endingId && !endConditions.some((ending) => ending.end_condition_id === draft.endingId && ending.outcome_tag === "lose"))
                throw new Error("Choose an existing defeat ending.");
            if (draft.recoveryLocationId && (!maps.length || !entities.some((entity) => entity.entity_type === "location" && entity.entity_id === draft.recoveryLocationId)))
                throw new Error("Choose a location from a story with a map.");
            if (existing && (!config || !Array.isArray(config.encounters)))
                throw new Error("This story has an unsupported combat configuration. Keep it unchanged.");
            const prior = editingIndex === null ? null : encounters[editingIndex] as Record<string, unknown> | undefined;
            if (editingIndex !== null && typeof prior?.encounter_id !== "string")
                throw new Error("This encounter is no longer available to edit.");
            const result = buildCombatTemplate(draft, scenario.state_schema ?? {}, typeof prior?.encounter_id === "string" ? prior.encounter_id : generateClientActionId());
            const next = editingIndex === null ? [...encounters, result.encounter] : encounters.map((item, index) => index === editingIndex ? result.encounter : item);
            saveFields({ rules: { ...rules, fantasy_combat: { ...config, encounters: next } }, state_schema: result.stateSchema });
            setDraft(emptyDraft());
            setError("");
            setOpen(false);
            setEditingIndex(null);
        }
        catch (caught) {
            setError(caught instanceof Error ? caught.message : "Could not add this encounter.");
        }
    };
    return <section aria-labelledby="combat-creator-heading" className="space-y-3 border-t border-border-subtle pt-6">
    <h2 id="combat-creator-heading" className="font-display text-heading text-content">Combat encounters</h2>
    <p className="text-meta text-content-muted">Create a one-on-one encounter. A yes/no tracked value decides when it becomes available; set that value with a rule.</p>
    {encounters.length > 0 && <ul className="space-y-2">{encounters.map((item, index) => {
                const record = item && typeof item === "object" ? item as Record<string, unknown> : {};
                const existingDraft = readCombatDraft(item);
                return <li key={typeof record.encounter_id === "string" ? record.encounter_id : index} className="flex items-center justify-between gap-3 border border-border-subtle p-3"><div><span>{typeof record.title === "string" ? record.title : "Encounter"}</span>{!existingDraft && <p className="text-meta text-content-muted">This advanced configuration cannot be edited here.</p>}</div><div className="flex gap-4">{existingDraft && <button type="button" className="min-h-11 text-content-muted underline" onClick={() => { setDraft(typeof existingHealth === "number" ? { ...existingDraft, player: { ...existingDraft.player, health: String(existingHealth) } } : existingDraft); setEditingIndex(index); setError(""); setOpen(true); }}>Edit</button>}<button type="button" className="min-h-11 text-content-muted underline" onClick={() => { setOpen(false); setEditingIndex(null); saveFields({ rules: { ...rules, fantasy_combat: { ...config, encounters: encounters.filter((_, position) => position !== index) } } }); }}>Remove</button></div></li>;
            })}</ul>}
    {!isOpen && <Button type="button" variant="secondary" onClick={() => { setDraft({ ...emptyDraft(), player: { ...EMPTY_ACTOR, health: typeof existingHealth === "number" ? String(existingHealth) : "" } }); setOpen(true); }}>Add combat encounter</Button>}
    {isOpen && <form onSubmit={save} className="space-y-4 rounded-lg border border-border-subtle bg-surface-raised p-4">
      <label className="block text-meta">Encounter title<input required value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} className="mt-1 block min-h-11 w-full border border-border-strong bg-surface-inset px-3 text-content"/></label>
      <label className="block text-meta">Available when this value is yes<select required value={draft.trigger} onChange={(event) => setDraft({ ...draft, trigger: event.target.value })} className="mt-1 block min-h-11 w-full border border-border-strong bg-surface-inset px-3 text-content"><option value="">Choose a yes/no value</option>{options.map((option) => <option key={option.path} value={option.path}>{option.label}</option>)}</select></label>
      {!options.length && <p className="text-meta text-content-muted">First add a yes/no value under Tracked values.</p>}
      <details className="text-meta text-content-muted"><summary className="min-h-11 cursor-pointer py-3">How combat values work</summary><p>Higher speed acts first. Accuracy and luck determine hit frequency without dice; attack, armor and luck determine damage. The player’s starting health is shared across encounters.</p></details>
      {(["player", "opponent"] as const).map((side) => <fieldset key={side} className="space-y-3"><legend className="font-semibold">{side === "player" ? "Player" : "Opponent"}</legend><div className="grid gap-3 sm:grid-cols-2">{ACTOR_FIELDS.map(({ key, label }) => <label key={key} className="block text-meta">{label}<input type="number" required min={key === "health" || key === "max_health" ? 1 : 0} max={key === "accuracy" || key === "luck" ? 100 : 10000} step={1} readOnly={side === "player" && key === "health" && typeof existingHealth === "number"} value={draft[side][key]} onChange={(event) => updateActor(side, key, event.target.value)} className="mt-1 block min-h-11 w-full border border-border-strong bg-surface-inset px-3 text-content"/></label>)}</div></fieldset>)}
      <label className="block text-meta">Player attack tag (optional)<input maxLength={128} value={draft.playerAttackTag} onChange={(event) => setDraft({ ...draft, playerAttackTag: event.target.value })} className="mt-1 block min-h-11 w-full border border-border-strong bg-surface-inset px-3 text-content"/></label>
      <label className="block text-meta">Tag required to damage opponent (optional)<input maxLength={128} value={draft.opponentRequiredTag} onChange={(event) => setDraft({ ...draft, opponentRequiredTag: event.target.value })} className="mt-1 block min-h-11 w-full border border-border-strong bg-surface-inset px-3 text-content"/></label>
      <p className="text-meta text-content-muted">When a tag is required, the player’s attack must have the same tag so the encounter can be won.</p>
      <label className="block text-meta">After player defeat<select value={draft.outcomeKind} onChange={(event) => setDraft({ ...draft, outcomeKind: event.target.value as CombatDraft["outcomeKind"] })} className="mt-1 block min-h-11 w-full border border-border-strong bg-surface-inset px-3 text-content"><option value="recover">Recover and continue</option><option value="end">Use a defeat ending</option></select></label>
      <label className="block text-meta">{draft.outcomeKind === "recover" ? "Player health after defeat" : "Alternative recovery health (optional)"}<input type="number" required={draft.outcomeKind === "recover"} min={1} max={10000} step={1} value={draft.recoveryHealth} onChange={(event) => setDraft({ ...draft, recoveryHealth: event.target.value, recoveryLocationId: event.target.value ? draft.recoveryLocationId : "" })} className="mt-1 block min-h-11 w-full border border-border-strong bg-surface-inset px-3 text-content"/></label>
      {maps.length > 0 && draft.recoveryHealth.trim() && <label className="block text-meta">Recovery location (optional)<select value={draft.recoveryLocationId} onChange={(event) => setDraft({ ...draft, recoveryLocationId: event.target.value })} className="mt-1 block min-h-11 w-full border border-border-strong bg-surface-inset px-3 text-content"><option value="">Stay at current location</option>{entities.filter((entity) => entity.entity_type === "location").map((entity) => <option key={entity.entity_id} value={entity.entity_id}>{entity.canonical_name}</option>)}</select></label>}
      <label className="block text-meta">{draft.outcomeKind === "end" ? "Defeat ending" : "Alternative defeat ending (optional)"}<select required={draft.outcomeKind === "end"} value={draft.endingId} onChange={(event) => setDraft({ ...draft, endingId: event.target.value })} className="mt-1 block min-h-11 w-full border border-border-strong bg-surface-inset px-3 text-content"><option value="">Choose a defeat ending</option>{endConditions.filter((ending) => ending.outcome_tag === "lose").map((ending) => <option key={ending.end_condition_id} value={ending.end_condition_id}>{ending.outcome_title}</option>)}</select></label>
      {draft.outcomeKind === "end" && !endConditions.some((ending) => ending.outcome_tag === "lose") && <p className="text-meta text-content-muted">Add a defeat ending in Endings first.</p>}
      <p className="text-meta text-content-muted">Zero health ends combat. The selected default is applied automatically. Alternative outcomes are saved for future use.</p>
      {error && <p role="alert" className="text-danger">{error}</p>}
      <div className="flex flex-wrap gap-3"><Button type="submit">{editingIndex === null ? "Add encounter" : "Save encounter"}</Button><Button type="button" variant="secondary" onClick={() => { setOpen(false); setEditingIndex(null); setDraft(emptyDraft()); setError(""); }}>Cancel</Button></div>
    </form>}
  </section>;
}
