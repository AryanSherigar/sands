import { useGuide } from "../../hooks/useGuide";
import type { EntityResponse } from "../../types/entity.types";

const FIELD = "scene_character_ids";
const MAX_CHARACTERS = 2;

export function ScenePortraitSetup({ characters }: { characters: EntityResponse[] }) {
  const { scenario, saveFields } = useGuide();
  if (!scenario || scenario.genre_tags?.[0] !== "Slice of Life") return null;
  const isSimple = scenario.mode === "newbie";
  const schema = scenario.state_schema ?? {};
  const field = schema[FIELD];
  if (!isSimple && field && (field.type !== "list" || field.item_type !== "entity_ref" || field.hidden || (field.entity_type && field.entity_type !== "character"))) {
    return <p className="text-meta text-content-muted">The scene character value has an incompatible configuration. Update it in the full editor to enable portraits.</p>;
  }
  const initial = isSimple ? scenario.rules?.portrait_opening_ids : field?.initial;
  const selected = Array.isArray(initial) ? initial.filter((item): item is string => typeof item === "string") : [];
  const withAvatars = characters.filter((character) => character.avatar_url);
  if (!withAvatars.length) return null;
  const toggle = (id: string, checked: boolean) => {
    const next = checked ? [...selected, id] : selected.filter((item) => item !== id);
    if (isSimple) {
      saveFields({ rules: { ...scenario.rules, portrait_opening_ids: next } });
    } else {
      saveFields({ state_schema: { ...schema, [FIELD]: { ...field, type: "list", item_type: "entity_ref", entity_type: "character", initial: next } } });
    }
  };
  return <fieldset className="space-y-2 border-t border-border-subtle pt-4">
    <legend className="font-medium text-content">Characters in the opening scene</legend>
    <p className="text-meta text-content-muted">Choose up to two characters with animated portraits.{!isSimple && " Use rules to update the scene character list during play."}</p>
    {withAvatars.map((character) => <label key={character.entity_id} className="flex items-center gap-2 text-sm text-content">
      <input type="checkbox" checked={selected.includes(character.entity_id)} disabled={!selected.includes(character.entity_id) && selected.length >= MAX_CHARACTERS} onChange={(event) => toggle(character.entity_id, event.target.checked)} />
      {character.canonical_name}
    </label>)}
  </fieldset>;
}
