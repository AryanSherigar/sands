import { useEffect, useState } from "react";
import {
  IconBackpack,
  IconBook2,
  IconFlag,
  IconMapPin,
  IconUsers,
  IconX,
} from "@tabler/icons-react";
import { buildFantasyViewModel, FantasyAccord } from "../../../utils/buildFantasyViewModel";
import { FantasyCharacterCard } from "./FantasyCharacterCard";
import type { DossierTab, FantasyDossierProps } from "./FantasyDossier.types";

function DossierHeader({ folioTitle, onClose }: { folioTitle: string; onClose: () => void }) {
  return (
    <div className="p-4 border-b border-[#382E25] bg-[#171310] shrink-0">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <IconBook2 size={20} className="text-[#C5A059]" />
          <h2 className="font-serif text-[18px] font-bold text-[#F5EEDB] tracking-tight">World Dossier</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[#C5A059] text-[11px] font-mono tracking-wider">{folioTitle}</span>
          <button type="button" onClick={onClose} aria-label="Close dossier" className="text-[#8C7A6B] hover:text-[#EDE0CA]">
            <IconX size={16} />
          </button>
        </div>
      </div>
      <p className="font-serif text-[13px] text-[#B5A593]">Characters and world details</p>
    </div>
  );
}

function DossierNav({
  activeTab,
  onSelectTab,
  hasMap,
  npcCount,
  onOpenCodex,
}: {
  activeTab: DossierTab;
  onSelectTab: (tab: DossierTab) => void;
  hasMap: boolean;
  npcCount: number;
  onOpenCodex: () => void;
}) {
  return (
    <nav aria-label="Dossier Tabs" className="flex border-b border-[#382E25] bg-[#14110E] shrink-0 overflow-x-auto no-scrollbar">
      <button
        type="button"
        onClick={() => onSelectTab("party")}
        className={`flex items-center gap-1.5 px-3.5 py-2.5 font-serif text-[13px] shrink-0 transition-colors ${
          activeTab === "party" ? "text-[#F5EEDB] border-b-2 border-[#C5A059] bg-[#1E1813] font-medium" : "text-[#8C7A6B] hover:text-[#EDE0CA]"
        }`}
      >
        <IconUsers size={16} className="text-[#C5A059]" />
        <span>Party &amp; NPCs</span>
        <span className="ml-1 px-1.5 py-0.2 rounded-full bg-[#C5A059]/20 text-[#C5A059] font-mono text-[10px]">{npcCount}</span>
      </button>
      <button
        type="button"
        onClick={() => onSelectTab("quests")}
        className={`flex items-center gap-1.5 px-3.5 py-2.5 font-serif text-[13px] shrink-0 transition-colors ${
          activeTab === "quests" ? "text-[#F5EEDB] border-b-2 border-[#C5A059] bg-[#1E1813] font-medium" : "text-[#8C7A6B] hover:text-[#EDE0CA]"
        }`}
      >
        <IconFlag size={16} />
        <span>Quests</span>
      </button>
      <button
        type="button"
        onClick={() => onSelectTab("relics")}
        className={`flex items-center gap-1.5 px-3.5 py-2.5 font-serif text-[13px] shrink-0 transition-colors ${
          activeTab === "relics" ? "text-[#F5EEDB] border-b-2 border-[#C5A059] bg-[#1E1813] font-medium" : "text-[#8C7A6B] hover:text-[#EDE0CA]"
        }`}
      >
        <IconBackpack size={16} />
        <span>Relics</span>
      </button>
      {hasMap && (
        <button
          type="button"
          onClick={() => onSelectTab("map")}
          className={`flex items-center gap-1.5 px-3.5 py-2.5 font-serif text-[13px] shrink-0 transition-colors ${
            activeTab === "map" ? "text-[#F5EEDB] border-b-2 border-[#C5A059] bg-[#1E1813] font-medium" : "text-[#8C7A6B] hover:text-[#EDE0CA]"
          }`}
        >
          <span>Map</span>
        </button>
      )}
      <button type="button" onClick={onOpenCodex} className="flex items-center gap-1.5 px-3.5 py-2.5 font-serif text-[13px] text-[#8C7A6B] hover:text-[#EDE0CA] shrink-0">
        <IconBook2 size={16} />
        <span>Codex</span>
      </button>
    </nav>
  );
}

function AccordCard({ accord }: { accord: FantasyAccord }) {
  return (
    <div className="p-3 rounded bg-[#1A1612] border border-[#382E25] shadow-sm">
      <div className="flex items-center justify-between mb-1">
        <span className="font-mono text-[10px] text-[#C5A059] uppercase tracking-wider flex items-center gap-1">
          <IconFlag size={12} />
          <span>Current Accord</span>
        </span>
        <span className="font-mono text-[10px] text-[#8C7A6B]">{accord.stageLabel}</span>
      </div>
      <h3 className="font-serif text-[15px] font-semibold text-[#F5EEDB] leading-tight">{accord.title}</h3>
      <p className="font-serif text-[12px] text-[#B5A593] mt-1 leading-snug">{accord.summary}</p>
      {accord.stageProgress !== null && <div className="mt-2.5 w-full bg-[#120F0D] h-1.5 rounded overflow-hidden border border-[#382E25]">
        <div className="bg-gradient-to-r from-[#9C6D37] to-[#C5A059] h-full rounded" style={{ width: `${accord.stageProgress}%` }} />
      </div>}
    </div>
  );
}

function DossierFooter({ onOpenCodex }: { onOpenCodex: () => void }) {
  return (
    <div className="p-4 border-t border-[#382E25] bg-[#171310] shrink-0">
      <button
        type="button"
        onClick={onOpenCodex}
        className="flex items-center justify-center gap-1.5 w-full py-2.5 px-3 rounded bg-[#201A15] hover:bg-[#2A221C] text-[#F5EEDB] font-serif text-[13px] border border-[#4A3C2F] shadow-sm transition-colors cursor-pointer"
      >
        <IconBook2 size={16} className="text-[#C5A059]" />
        <span>Examine Complete Folio Archives</span>
      </button>
    </div>
  );
}

export function FantasyDossier({
  playthrough,
  canTalk = true,
  map,
  mapRequest,
  onClose,
  onTalk,
  onOpenCodex,
}: FantasyDossierProps) {
  const [tab, setTab] = useState<DossierTab>("party");
  const view = buildFantasyViewModel(playthrough);
  const [expandedId, setExpandedId] = useState<string | null>(view.characters[0]?.id ?? null);

  useEffect(() => {
    if (mapRequest) setTab("map");
  }, [mapRequest]);

  return (
    <aside aria-label="World Dossier" className="h-full flex flex-col justify-between overflow-hidden bg-[#120F0D] border-l border-[#382E25] shadow-2xl">
      <DossierHeader folioTitle={view.folioTitle} onClose={onClose} />
      <DossierNav activeTab={tab} onSelectTab={setTab} hasMap={Boolean(map)} npcCount={view.characters.length} onOpenCodex={onOpenCodex} />
      <div className="flex-1 p-3.5 space-y-4 overflow-y-auto bg-[#14110E] scrollbar-minimal">
        {tab === "party" && (
          <>
            {view.currentAccord && <AccordCard accord={view.currentAccord} />}
            <section className="p-3 rounded bg-[#1A1612] border border-[#382E25]">
              <h3 className="font-serif text-[#F5EEDB]">{playthrough.character_name}</h3>
              {(playthrough.custom_fields ?? []).map((field) => <p key={field.key}>{field.label}: {field.value}</p>)}
              {(playthrough.player_stats ?? []).filter((stat) => ["string", "number", "boolean"].includes(typeof stat.value)).map((stat) => <p key={stat.key}>{stat.label}: {String(stat.value)}</p>)}
            </section>
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-[#2B231B] pb-1.5">
                <div className="flex items-center gap-1.5">
                  <IconMapPin size={14} className="text-[#C5A059]" />
                  <h4 className="font-mono text-[11px] text-[#8C7A6B] uppercase tracking-wider">
                    Known characters ({view.characters.length})
                  </h4>
                </div>
                <span className="font-mono text-[10px] text-[#D4A373] flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#C5A059] animate-pulse" />
                  Known
                </span>
              </div>
              {view.characters.map((char) => (
                <FantasyCharacterCard
                  key={char.id}
                  character={char}
                  isExpanded={expandedId === char.id}
                  canTalk={canTalk}
                  onToggleExpand={() => setExpandedId(expandedId === char.id ? null : char.id)}
                  onTalk={onTalk}
                />
              ))}
            </div>
            {view.factions.map((faction) => <section key={faction.id} className="p-3 rounded bg-[#1A1612] border border-[#382E25]"><h3>{faction.name}</h3>{faction.attributes.map((attribute) => <p key={attribute.label}>{attribute.label}: {String(attribute.value)}</p>)}</section>)}
          </>
        )}
        {tab === "quests" && (
          <div className="space-y-3">
            {view.currentAccord && <AccordCard accord={view.currentAccord} />}
            {playthrough.objectives.map((obj, i) => (
              <div key={i} className="p-3 rounded bg-[#171310] border border-[#382E25]">
                <span className="font-mono text-[10px] text-[#C5A059] uppercase">{obj.outcome_tag === "win" ? "Victory Accord" : "Peril"}</span>
                <h5 className="font-serif text-[14px] font-semibold text-[#F5EEDB] mt-1">{obj.outcome_title}</h5>
                <p className="font-serif text-[12px] text-[#B5A593] mt-1">{obj.outcome_text}</p>
              </div>
            ))}
          </div>
        )}
        {tab === "relics" && (
          <div className="space-y-3">
            {view.relics.length === 0 ? (
              <p className="font-serif text-[13px] text-[#8C7A6B]">Your ledger holds no relics yet.</p>
            ) : (
              view.relics.map((item) => (
                <div key={item.entity_id} className="p-3 rounded bg-[#171310] border border-[#382E25]">
                  <h5 className="font-serif text-[14px] font-semibold text-[#F5EEDB]">{item.canonical_name}</h5>
                  {item.description && <p className="font-serif text-[12px] text-[#B5A593] mt-1">{item.description}</p>}
                </div>
              ))
            )}
          </div>
        )}
        {tab === "map" && map}
      </div>
      <DossierFooter onOpenCodex={onOpenCodex} />
    </aside>
  );
}
