import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import {
  AMBITION_PRESETS,
  BUILTIN_STANCE_OPTIONS,
  BUILTIN_TRAIT_OPTIONS,
  DEFAULT_HEIR_AGE,
  DEFAULT_HEIR_TRAIT_IDS,
} from "../../constants/strategyAuthoring";
import {
  getAmbitionPresetId,
  removeFaction,
  setLeaderAmbitionPreset,
  updateFaction,
  updateLeader,
} from "../../lib/strategyDocument";
import { AnimatedPortrait } from "@/shared/components/AnimatedPortrait/AnimatedPortrait";
import { StrategyFactionStats } from "./StrategyFactionStats";
import { LeaderAvatarCreatorModal } from "./LeaderAvatarCreatorModal";
import { StrategyLeaderHistoryEditor } from "./StrategyLeaderHistoryEditor";
import type { StrategyLeader } from "../../types/strategyDocument.types";
import type { StrategyFactionCardProps } from "./StrategyWorkspace.types";

const NO_CAPITAL = "";

const replaceTrait = (traitIds: string[], slot: number, traitId: string): string[] =>
  Object.assign([...traitIds], { [slot]: traitId });

function renderLeaderThumbnail(leader: StrategyLeader, factionName: string): React.ReactNode {
  if (leader.avatar_url) {
    return (
      <AnimatedPortrait
        avatarUrl={leader.avatar_url}
        portraitUrl={leader.portrait_url ?? undefined}
        fallbackSrc="data:image/svg+xml;utf8,<svg></svg>"
        label={`${leader.name} of ${factionName}`}
      />
    );
  }
  if (leader.portrait_url) {
    return (
      <img
        src={leader.portrait_url}
        alt={`${leader.name} portrait`}
        className="w-full h-full object-cover"
      />
    );
  }
  return <span className="text-[11px] text-text-muted">No avatar</span>;
}

export const StrategyFactionCard: React.FC<StrategyFactionCardProps> = ({
  factionId,
  fields,
  regions,
  onEdit,
}) => {
  const faction = fields.factions.find((item) => item.id === factionId);
  const leader = fields.leaders.find((item) => item.faction_id === factionId);
  const [isAvatarModalOpen, setIsAvatarModalOpen] = useState(false);
  if (!faction || !leader) return null;

  const traitOptions = BUILTIN_TRAIT_OPTIONS.map((item) => ({ value: item.id, label: item.name }));
  const regionOptions = [
    { value: NO_CAPITAL, label: "Choose a capital…" },
    ...regions.map((region) => ({ value: region.id, label: region.name })),
  ];
  const ambitionOptions = AMBITION_PRESETS.map((item) => ({ value: item.id, label: item.name }));
  const stanceOptions = [
    { value: "", label: "Default dynamic AI" },
    ...BUILTIN_STANCE_OPTIONS.map((item) => ({ value: item.id, label: `${item.label} — ${item.description}` })),
  ];

  return (
    <li className="space-y-3 rounded-md border border-border-subtle bg-surface-raised p-4">
      <div className="flex items-center gap-2">
        <input
          type="color"
          aria-label={`${faction.name} color`}
          value={faction.color}
          onChange={(event) => onEdit((current) => updateFaction(current, factionId, { color: event.target.value }))}
        />
        <Input
          aria-label="Faction name"
          value={faction.name}
          onChange={(event) => onEdit((current) => updateFaction(current, factionId, { name: event.target.value }))}
        />
        <Button variant="ghost" size="sm" onClick={() => onEdit((current) => removeFaction(current, factionId))}>
          Remove
        </Button>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={faction.is_playable}
          onChange={(event) => onEdit((current) => updateFaction(current, factionId, { is_playable: event.target.checked }))}
        />
        Players can pick this faction
      </label>
      <StrategyFactionStats faction={faction} onEdit={onEdit} />
      <label className="block space-y-1 text-sm">
        Capital
        <Select
          value={faction.capital_region_id ?? NO_CAPITAL}
          options={regionOptions}
          onChange={(event) =>
            onEdit((current) => updateFaction(current, factionId, { capital_region_id: event.target.value || null }))
          }
        />
      </label>
      <label htmlFor={`faction-stance-${factionId}`} className="block space-y-1 text-sm">
        AI starting stance
        <Select
          id={`faction-stance-${factionId}`}
          value={faction.stance_ids?.[0] ?? ""}
          options={stanceOptions}
          onChange={(event) => {
            const val = event.target.value;
            onEdit((current) =>
              updateFaction(current, factionId, {
                stance_ids: val ? [val] : null,
              }),
            );
          }}
        />
      </label>
      <label className="block space-y-1 text-sm">
        Leader name
        <Input
          value={leader.name}
          onChange={(event) => onEdit((current) => updateLeader(current, leader.id, { name: event.target.value }))}
        />
      </label>
      {[0, 1].map((slot) => (
        <label key={slot} className="block space-y-1 text-sm">
          Leader trait {slot + 1}
          <Select
            value={leader.trait_ids[slot] ?? ""}
            options={traitOptions}
            onChange={(event) =>
              onEdit((current) => updateLeader(current, leader.id, { trait_ids: replaceTrait(leader.trait_ids, slot, event.target.value) }))
            }
          />
        </label>
      ))}
      <label className="block space-y-1 text-sm">
        Leader ambition
        <Select
          value={getAmbitionPresetId(fields, leader)}
          options={ambitionOptions}
          onChange={(event) => onEdit((current) => setLeaderAmbitionPreset(current, leader.id, event.target.value))}
        />
      </label>
      <StrategyLeaderHistoryEditor
        leader={leader}
        factionName={faction.name}
        onEdit={onEdit}
      />
      <div className="space-y-2 rounded border border-border-subtle bg-surface-inset p-3">
        <label className="flex items-center gap-2 text-sm font-medium">
          <input
            type="checkbox"
            checked={Boolean(leader.heir)}
            onChange={(event) => {
              const isDesignated = event.target.checked;
              onEdit((current) =>
                updateLeader(current, leader.id, {
                  heir: isDesignated
                    ? {
                        id: `${leader.id}_heir`,
                        name: `${leader.name} the Younger`,
                        age: DEFAULT_HEIR_AGE,
                        trait_ids: [...DEFAULT_HEIR_TRAIT_IDS],
                      }
                    : null,
                }),
              );
            }}
          />
          Designate dynastic heir
        </label>
        {leader.heir && (
          <div className="grid gap-2 sm:grid-cols-3 pt-1">
            <label className="block space-y-1 text-xs">
              Heir name
              <Input
                value={leader.heir.name}
                onChange={(event) =>
                  onEdit((current) =>
                    updateLeader(current, leader.id, {
                      heir: { ...leader.heir!, name: event.target.value },
                    }),
                  )
                }
              />
            </label>
            <label className="block space-y-1 text-xs">
              Heir age
              <Input
                type="number"
                min={0}
                max={100}
                value={leader.heir.age}
                onChange={(event) =>
                  onEdit((current) =>
                    updateLeader(current, leader.id, {
                      heir: { ...leader.heir!, age: Number(event.target.value) || 0 },
                    }),
                  )
                }
              />
            </label>
            <label className="block space-y-1 text-xs">
              Heir trait
              <Select
                value={leader.heir.trait_ids[0] ?? ""}
                options={traitOptions}
                onChange={(event) =>
                  onEdit((current) =>
                    updateLeader(current, leader.id, {
                      heir: { ...leader.heir!, trait_ids: [event.target.value] },
                    }),
                  )
                }
              />
            </label>
          </div>
        )}
      </div>
      <div className="pt-3 border-t border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded border border-border-subtle overflow-hidden bg-surface-inset flex items-center justify-center">
            {renderLeaderThumbnail(leader, faction.name)}
          </div>
          <div>
            <p className="text-xs font-semibold text-text-primary">Leader Avatar</p>
            <p className="text-[11px] text-text-muted">
              {leader.avatar_url ? "Animated 2D Mesh Active" : "No animated avatar"}
            </p>
          </div>
        </div>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => setIsAvatarModalOpen(true)}
        >
          {leader.avatar_url ? "Edit Avatar" : "Generate Avatar"}
        </Button>
      </div>

      <LeaderAvatarCreatorModal
        isOpen={isAvatarModalOpen}
        onClose={() => setIsAvatarModalOpen(false)}
        leaderName={leader.name}
        factionName={faction.name}
        currentAvatarUrl={leader.avatar_url}
        currentPortraitUrl={leader.portrait_url}
        onSavePortrait={(url) =>
          onEdit((current) => updateLeader(current, leader.id, { portrait_url: url }))
        }
        onSave={(url) =>
          onEdit((current) => updateLeader(current, leader.id, { avatar_url: url }))
        }
      />
    </li>
  );
};
