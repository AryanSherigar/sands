import React from "react";
import {
  deriveLeaderMoodTag,
  generateHeraldicCrestSvg,
} from "../utils/negotiationStance.utils";
import type { NegotiationRulerDossierProps } from "./NegotiationRulerDossier.types";
import { RulerMeshAvatar } from "./RulerMeshAvatar";

export const NegotiationRulerDossier: React.FC<NegotiationRulerDossierProps> = ({
  leaderName,
  factionName,
  portraitUrl,
  avatarUrl,
  expression,
  isSpeaking,
  traitIds = [],
  isAtWar = false,
  playerLeaderName,
  playerFactionName,
  playerPortraitUrl,
  playerGold,
  playerLevies,
}) => {
  const moodTag = deriveLeaderMoodTag(traitIds, isAtWar);
  const fallbackCrest = generateHeraldicCrestSvg(factionName);
  const formattedLevies = Number(playerLevies).toLocaleString("en-US");

  return (
    <aside className="w-80 shrink-0 h-full bg-gradient-to-b from-surface-variant/70 via-app-bg to-surface-dim/80 p-6 flex flex-col justify-between shadow-md relative z-10 border-r border-outline-variant/30">
      <div className="relative z-10 flex flex-col items-center">
        <div className="flex items-center gap-1.5 mb-4 text-outline font-sans text-xs uppercase tracking-widest font-semibold">
          <span className="material-symbols-outlined text-[14px]">shield</span>
          <span>Sovereign of {factionName}</span>
        </div>

        <div className="relative w-64 h-[350px] rounded-xl overflow-hidden shadow-xl bg-surface-container-highest group border border-outline-variant/40">
          <div className="absolute top-2 left-2 w-3 h-3 bg-secondary-fixed/60 rounded-tl-sm pointer-events-none z-10" />
          <div className="absolute top-2 right-2 w-3 h-3 bg-secondary-fixed/60 rounded-tr-sm pointer-events-none z-10" />
          <div className="absolute bottom-2 left-2 w-3 h-3 bg-secondary-fixed/60 rounded-bl-sm pointer-events-none z-10" />
          <div className="absolute bottom-2 right-2 w-3 h-3 bg-secondary-fixed/60 rounded-br-sm pointer-events-none z-10" />

          <RulerMeshAvatar
            avatarUrl={avatarUrl}
            portraitUrl={portraitUrl}
            fallbackCrest={fallbackCrest}
            leaderName={leaderName}
            factionName={factionName}
            expression={expression}
            isSpeaking={isSpeaking}
          />

          <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-on-surface/60 via-on-surface/20 to-transparent pointer-events-none" />

          <div className="absolute bottom-3 right-3 bg-parchment-panel/90 text-on-surface text-xs font-semibold px-2 py-0.5 rounded shadow-sm backdrop-blur-sm border border-outline-variant/30">
            {factionName}
          </div>
        </div>

        <div className="mt-4 text-center">
          <h2 className="font-serif text-2xl font-semibold text-on-surface">
            {leaderName}
          </h2>
          <div className="inline-flex items-center gap-1.5 mt-1 px-3 py-0.5 rounded-full bg-surface-container shadow-sm border border-outline-variant/30">
            <span className="w-2 h-2 rounded-full bg-secondary" />
            <span className="font-sans text-xs text-on-surface-variant italic font-medium">
              {moodTag}
            </span>
          </div>
        </div>
      </div>

      <div className="relative z-10 pt-4 bg-parchment-panel/70 backdrop-blur-sm p-3.5 rounded-xl shadow-sm border border-outline-variant/30">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full overflow-hidden bg-primary-container shrink-0 shadow-md border border-secondary/40">
            {playerPortraitUrl ? (
              <img
                src={playerPortraitUrl}
                alt={playerLeaderName}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-primary text-on-primary font-serif font-bold text-lg">
                {playerLeaderName.charAt(0)}
              </div>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <span className="font-serif text-base font-semibold text-on-surface truncate">
                {playerLeaderName}
              </span>
              <span className="font-sans text-[10px] text-primary bg-primary-fixed/60 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">
                You
              </span>
            </div>
            <p className="font-sans text-xs text-outline truncate">{playerFactionName}</p>
          </div>
        </div>

        <div className="mt-2.5 pt-2 border-t border-outline-variant/20 flex items-center justify-between text-xs font-stat-numeric text-on-surface-variant">
          <span className="flex items-center gap-1">
            <span className="material-symbols-outlined text-[15px] text-secondary">
              monetization_on
            </span>
            {playerGold} Gold
          </span>
          <span className="flex items-center gap-1">
            <span className="material-symbols-outlined text-[15px] text-meadow-green">
              swords
            </span>
            {formattedLevies} Levies
          </span>
        </div>
      </div>
    </aside>
  );
};
