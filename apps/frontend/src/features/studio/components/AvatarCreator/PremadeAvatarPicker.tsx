import React from "react";
import { usePremadeAvatars } from "../../hooks/usePremadeAvatars";
import type { PremadeAvatarPickerProps } from "./PremadeAvatarPicker.types";

export const PremadeAvatarPicker: React.FC<PremadeAvatarPickerProps> = ({
  selectedAvatarUrl,
  onSelect,
}) => {
  const { data: avatars } = usePremadeAvatars();
  if (!avatars || avatars.length === 0) return null;

  const selectedAvatar = avatars.find((avatar) => avatar.avatar_url === selectedAvatarUrl);

  return (
    <section className="space-y-2" aria-label="Premade avatars">
      <h3 className="block text-xs font-semibold text-text-secondary">Start from a premade avatar</h3>
      <div className="grid grid-cols-4 gap-2">
        {avatars.map((avatar) => {
          const isSelected = avatar.avatar_url === selectedAvatarUrl;
          return (
            <button
              key={avatar.id}
              type="button"
              aria-pressed={isSelected}
              aria-label={`Use premade avatar ${avatar.name}`}
              onClick={() => onSelect(avatar)}
              className={`overflow-hidden rounded-md border bg-surface-inset text-center transition-colors ${
                isSelected ? "border-accent ring-2 ring-accent" : "border-border-subtle hover:border-border-strong"
              }`}
            >
              <img src={avatar.preview_url} alt="" className="aspect-square w-full object-cover object-top" />
              <span className="block truncate px-1 py-0.5 text-[11px] text-text-secondary">{avatar.name}</span>
            </button>
          );
        })}
      </div>
      {selectedAvatar?.credit && <p className="text-[11px] text-text-muted">{selectedAvatar.credit}</p>}
    </section>
  );
};
