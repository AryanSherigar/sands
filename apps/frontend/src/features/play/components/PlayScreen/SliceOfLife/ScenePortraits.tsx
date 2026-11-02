import { AnimatedPortrait } from "@/shared/components/AnimatedPortrait/AnimatedPortrait";
import type { ScenePortrait } from "../../../types/play.types";
import { useEffect, useState } from "react";
import { narrationPlayback } from "@/shared/lib/audio/narration-playback";

const FALLBACK = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='35' r='20' fill='%2388817a'/%3E%3Cpath d='M15 100a35 35 0 0170 0' fill='%2388817a'/%3E%3C/svg%3E";

export function ScenePortraits({ portraits, presentIds }: { portraits: ScenePortrait[]; presentIds: unknown }) {
  const [speaker, setSpeaker] = useState<string | null>(null);
  useEffect(() => narrationPlayback.onSpeakerChange(setSpeaker), []);
  if (!Array.isArray(presentIds)) return null;
  const visible = portraits.filter((portrait) => presentIds.includes(portrait.entity_id)).slice(0, 2);
  const speaking = speaker ? visible.filter((portrait) => portrait.name.trim().toLocaleLowerCase() === speaker.trim().toLocaleLowerCase()) : [];
  if (!visible.length) return null;
  return <aside aria-label="Characters in the scene" className="relative z-10 flex justify-center gap-3 px-4 py-1 xl:pointer-events-none xl:absolute xl:inset-x-4 xl:bottom-20 xl:justify-between">
    {visible.map((portrait) => <div key={portrait.entity_id} className="flex items-center gap-2 xl:flex-col">
      <div className="h-16 w-16 overflow-hidden rounded-lg bg-surface-raised xl:h-64 xl:w-44">
        <AnimatedPortrait avatarUrl={portrait.avatar_url} fallbackSrc={FALLBACK} label={portrait.name} isSpeaking={speaking.length === 1 && speaking[0].entity_id === portrait.entity_id} />
      </div>
      <span className="text-meta text-content-muted">{portrait.name}</span>
    </div>)}
  </aside>;
}
