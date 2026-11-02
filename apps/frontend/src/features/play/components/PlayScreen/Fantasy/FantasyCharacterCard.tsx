import {
  IconChevronUp,
  IconMaximize,
  IconMessage,
  IconShield,
} from "@tabler/icons-react";
import type { FantasyCharacterCardProps } from "./FantasyCharacterCard.types";
import type { FantasyCharacter } from "../../../utils/buildFantasyViewModel";

function ExpandedCardHeader({ onToggle }: { onToggle: () => void }) {
  return (
    <div className="flex items-center justify-between border-b border-[#382E25] pb-2 mb-2.5">
      <div className="flex items-center gap-1.5">
        <IconShield size={14} className="text-[#C5A059]" />
        <span className="font-mono text-[10px] text-[#C5A059] tracking-wider uppercase font-semibold">
          Expanded Folio Dossier
        </span>
      </div>
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center gap-1 text-[11px] text-[#B5A593] hover:text-[#F5EEDB] transition-colors"
      >
        <IconChevronUp size={13} />
        <span>Collapse</span>
      </button>
    </div>
  );
}

function ExpandedCardProfile({ character }: { character: FantasyCharacter }) {
  const disposition = character.disposition;
  return (
    <div className="flex gap-3 mb-3">
      <div className="relative w-24 h-28 rounded-md overflow-hidden shrink-0 bg-[#0C0A08] shadow-lg flex items-center justify-center border border-[#382E25]">
        {character.avatarUrl ? (
          <img src={character.avatarUrl} alt={character.name} className="w-full h-full object-cover" />
        ) : (
          <span className="font-serif text-3xl text-[#C5A059]">{character.initial}</span>
        )}
        <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-1 text-center">
          <span className="font-mono text-[9px] text-[#C5A059] uppercase tracking-widest">{character.role}</span>
        </div>
      </div>
      <div className="flex-1 min-w-0 flex flex-col justify-between">
        <div>
          <h5 className="font-serif font-bold text-[17px] text-[#F5EEDB] leading-tight">{character.name}</h5>
          <p className="font-serif text-[12px] text-[#C5A059] italic mt-0.5">{character.title}</p>
          {character.bio && (
            <p className="font-serif text-[11px] text-[#B5A593] leading-snug mt-1">{character.bio}</p>
          )}
        </div>
        {disposition && (
          <div className="pt-1 border-t border-[#2E251E]">
            <div className="flex justify-between font-mono text-[10px] text-[#8C7A6B] mb-0.5">
              <span>Disposition:</span>
              <span className="text-[#C5A059] font-semibold">{disposition.label}</span>
            </div>
            <div className="w-full bg-[#14110E] h-1.5 rounded overflow-hidden border border-[#382E25]">
              <div
                className="bg-gradient-to-r from-[#9C6D37] to-[#C5A059] h-full rounded"
                style={{ width: `${disposition.percent}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ExpandedCardAttributes({ character }: { character: FantasyCharacter }) {
  if (character.attributes.length === 0) return null;

  return (
    <div className="bg-[#14110E] p-2.5 rounded border border-[#2E251E] space-y-2 mb-2.5 font-serif text-[12px]">
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        {character.attributes.map((attr) => (
          <div key={attr.label}>
            <span className="text-[#8C7A6B] font-mono text-[10px] uppercase block">{attr.label}:</span>
            <span className="text-[#EDE0CA] font-medium truncate block">{String(attr.value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ExpandedCardActions({
  character,
  canTalk,
  onTalk,
}: {
  character: FantasyCharacter;
  canTalk: boolean;
  onTalk: (name: string) => void;
}) {
  return (
    <div className="pt-1">
      <button
        type="button"
        disabled={!canTalk}
        onClick={() => onTalk(character.name)}
        className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded bg-[#201A15] hover:bg-[#2A221C] border border-[#3E3224] text-[#F5EEDB] hover:text-[#EDE0CA] font-serif text-[12px] transition-colors disabled:opacity-50 cursor-pointer shadow-sm"
      >
        <IconMessage size={14} className="text-[#C5A059]" />
        <span>Confer Privately</span>
      </button>
    </div>
  );
}

function CompactCard({
  character,
  onToggle,
}: {
  character: FantasyCharacter;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="w-full text-left rounded-lg bg-[#1A1612] border border-[#382E25] hover:border-[#C5A059]/60 transition-all p-2.5 group cursor-pointer shadow-sm"
    >
      <div className="flex gap-2.5">
        <div className="w-12 h-12 rounded border border-[#C5A059]/50 overflow-hidden shrink-0 bg-[#0C0A08] shadow-md flex items-center justify-center">
          {character.avatarUrl ? (
            <img src={character.avatarUrl} alt={character.name} className="w-full h-full object-cover" />
          ) : (
            <span className="font-serif text-lg text-[#C5A059]">{character.initial}</span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between">
            <h5 className="font-serif font-bold text-[14px] text-[#F5EEDB] group-hover:text-[#C5A059] transition-colors truncate">
              {character.name}
            </h5>
            {character.disposition && (
              <span className="px-1.5 py-0.5 rounded bg-[#221C16] font-mono text-[10px] text-[#C5A059] border border-[#382E25] shrink-0">
                {character.disposition.label}
              </span>
            )}
          </div>
          <p className="font-serif text-[11px] text-[#C5A059] italic truncate">{character.title}</p>
          <div className="flex items-center justify-between mt-1 text-[11px] text-[#8C7A6B] font-serif">
            <span className="truncate">{character.inventoryArtifact ?? character.role}</span>
            <span className="flex items-center gap-0.5 text-[#C5A059] group-hover:translate-x-0.5 transition-transform text-[10px] font-mono shrink-0 ml-1">
              <IconMaximize size={12} />
              <span>Expand</span>
            </span>
          </div>
        </div>
      </div>
    </button>
  );
}

export function FantasyCharacterCard({
  character,
  isExpanded,
  canTalk,
  onToggleExpand,
  onTalk,
}: FantasyCharacterCardProps) {
  if (isExpanded) {
    return (
      <div className="rounded-lg bg-[#1B1510] border border-[#C5A059] shadow-xl p-3 relative transition-all duration-200">
        <ExpandedCardHeader onToggle={onToggleExpand} />
        <ExpandedCardProfile character={character} />
        <ExpandedCardAttributes character={character} />
        <ExpandedCardActions character={character} canTalk={canTalk} onTalk={onTalk} />
      </div>
    );
  }

  return <CompactCard character={character} onToggle={onToggleExpand} />;
}
