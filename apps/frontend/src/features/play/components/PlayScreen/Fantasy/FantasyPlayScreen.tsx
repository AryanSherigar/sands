import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePlayStore } from "../../../stores/play.store";
import { selectCanRetryTurn } from "../../../stores/play.selectors";
import { buildFantasyViewModel } from "../../../utils/buildFantasyViewModel";
import { FantasyHeader } from "./FantasyHeader";
import { FantasyStatusStrip } from "./FantasyStatusStrip";
import { EBookActionDrawer } from "../EBook/EBookActionDrawer";
import { FantasyDossier } from "./FantasyDossier";
import { FantasyDossierResizer } from "./FantasyDossierResizer";
import { useDossierResizer } from "../../../hooks/useDossierResizer";
import { EBookCanvas } from "../EBook/EBookCanvas";
import { EBookBottomBar } from "../EBook/EBookBottomBar";
import { EBookCodexDrawer } from "../EBook/EBookCodexDrawer";
import { ChronicleRecapModal } from "../EBook/ChronicleRecapModal";
import { RulesClipboardContainer } from "../../RulesClipboard/RulesClipboardContainer";
import { PhoneEcho } from "../../PhoneEcho/PhoneEcho";
import { MemoryDegradedBanner } from "../MemoryDegradedBanner";
import { PlaythroughEndedBanner } from "../PlaythroughEndedBanner";
import { Toast } from "@/shared/components/feedback/Toast";
import { MapViewer } from "../../MapViewer/MapViewer";
import { useFantasyCombat } from "../../../hooks/useFantasyCombat";
import { FantasyCombat } from "./FantasyCombat";
import type { FantasyPlayScreenProps } from "./FantasyPlayScreen.types";

export function FantasyPlayScreen({ scenarioSnapshot, mapState }: FantasyPlayScreenProps = {}) {
  const navigate = useNavigate();
  const playthrough = usePlayStore((s) => s.playthrough);
  const isSepia = usePlayStore((s) => s.ebook_theme === "antique-sepia");
  const isNarrating = usePlayStore((s) => s.is_narrating);
  const isCodexOpen = usePlayStore((s) => s.is_left_sidebar_open);
  const isChronicleOpen = usePlayStore((s) => s.is_chronicle_modal_open);
  const degraded = usePlayStore((s) => s.degraded_message);
  const quota = usePlayStore((s) => s.quota_notice_message);
  const truncated = usePlayStore((s) => s.input_truncated_message);
  const activeCheck = usePlayStore((s) => s.active_check);
  const activeRuleCheck = usePlayStore((s) => s.active_rule_check);
  const activeMinigame = usePlayStore((s) => s.active_minigame);
  const canRetry = usePlayStore(selectCanRetryTurn);
  const combat = useFantasyCombat(playthrough, isNarrating);

  const [isDossierOpen, setDossierOpen] = useState(() => window.matchMedia?.("(min-width: 1280px)").matches ?? false);
  const [mapRequest, setMapRequest] = useState(0);
  const [draft, setDraft] = useState<{ text: string; mode: "say"; requestId: number }>();
  const dossierButton = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);

  const {
    width: sidebarWidth,
    isDragging: isResizing,
    minWidth: minSidebarWidth,
    maxWidth: maxSidebarWidth,
    startDrag: startResize,
    handleKeyDown: handleResizeKeyDown,
  } = useDossierResizer();

  const toggleCodex = usePlayStore((s) => s.toggleLeftSidebar);
  const setCodexOpen = usePlayStore((s) => s.setLeftSidebarOpen);
  const closeChronicle = usePlayStore((s) => s.closeChronicleModal);
  const openChronicle = usePlayStore((s) => s.openChronicleModal);
  const submitTurn = usePlayStore((s) => s.submitTurn);
  const submitFantasyAction = usePlayStore((s) => s.submitFantasyAction);
  const continueTurn = usePlayStore((s) => s.continueTurn);
  const retryTurn = usePlayStore((s) => s.retryLastTurn);
  const clearDegraded = usePlayStore((s) => s.clearDegradedMessage);
  const clearQuota = usePlayStore((s) => s.clearQuotaNoticeMessage);
  const clearTruncated = usePlayStore((s) => s.clearInputTruncatedMessage);

  useEffect(() => {
    setCodexOpen(false);
  }, [setCodexOpen]);

  useEffect(() => {
    if (!isDossierOpen || window.matchMedia?.("(min-width: 1280px)").matches) return;
    const focusable = () => Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not([disabled]), [href], input, textarea, [tabindex]:not([tabindex="-1"])') ?? []);
    focusable()[0]?.focus();
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") { setDossierOpen(false); dossierButton.current?.focus(); return; }
      if (e.key !== "Tab") return;
      const items = focusable();
      if (!items.length) return;
      if (e.shiftKey && document.activeElement === items[0]) { e.preventDefault(); items[items.length - 1].focus(); }
      if (!e.shiftKey && document.activeElement === items[items.length - 1]) { e.preventDefault(); items[0].focus(); }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isDossierOpen]);

  if (!playthrough) return null;
  const view = buildFantasyViewModel(playthrough);
  const hasMap = Array.isArray(scenarioSnapshot?.maps) && scenarioSnapshot.maps.length > 0;
  const isEnded = Boolean(playthrough.ended_outcome_tag);
  const canAct = !isEnded && !playthrough.is_spectator && playthrough.can_act;
  const hasPendingAction = Boolean(activeCheck || activeRuleCheck || activeMinigame);
  const isActionBlocked = hasPendingAction || combat.isBlocked;
  const mechanics = playthrough.fantasy_mechanics;
  const locations = mechanics?.locations as Record<string, unknown> | undefined;
  const quests = playthrough.state?.quests as Record<string, unknown> | undefined;
  const retrieval = quests?.retrieval as Record<string, unknown> | undefined;
  const profileEnabled = playthrough.mode === "master" && mechanics?.version === 1 && mechanics.profile === "zegaris";
  const canRest = profileEnabled && typeof mechanics.energy_max === "number" && mechanics.energy_max > 0 && typeof mechanics.initial_energy === "number" && mechanics.rest_cost === 5 && typeof locations?.inn === "string" && playthrough.state.current_location_id === locations.inn;
  const canClaim = profileEnabled && typeof mechanics.bounty_reward === "number" && mechanics.bounty_reward >= 0 && typeof locations?.quest_giver === "string" && playthrough.state.current_location_id === locations.quest_giver && retrieval?.stage === "cremated";

  const handleTalk = (name: string) => {
    setDraft((curr) => ({ text: `I talk to ${name}.`, mode: "say", requestId: (curr?.requestId ?? 0) + 1 }));
    if (!window.matchMedia?.("(min-width: 1280px)").matches) setDossierOpen(false);
  };
  const handleOpenCodex = () => {
    if (!window.matchMedia?.("(min-width: 1280px)").matches) setDossierOpen(false);
    toggleCodex();
  };
  const handleCloseDossier = () => {
    setDossierOpen(false);
    dossierButton.current?.focus();
  };

  return (
    <div className={`fantasy-screen-root ${isSepia ? "fantasy-sepia" : ""} bg-[#0C0C0E] text-[#EDEDEF] font-sans text-sm antialiased selection:bg-[#CDBB8E]/20 selection:text-[#CDBB8E] min-h-screen overflow-x-hidden flex flex-col`}>
      <FantasyHeader
        scenarioTitle={view.scenarioTitle}
        folioTitle={view.folioTitle}
        turnNumber={view.turnNumber}
        isNarrating={isNarrating}
        isDossierOpen={isDossierOpen}
        dossierButton={dossierButton}
        onBack={() => navigate("/discover")}
        onOpenCodex={handleOpenCodex}
        onOpenChronicle={openChronicle}
        onOpenMap={hasMap ? () => { setDossierOpen(true); setMapRequest((r) => r + 1); } : undefined}
        onToggleDossier={() => setDossierOpen(!isDossierOpen)}
      />

      <FantasyStatusStrip status={view.status} />

      <div
        style={{ "--dossier-w": `${sidebarWidth}px` } as React.CSSProperties}
        className="pt-[124px] flex-1 flex relative"
      >
        <main
          className={`flex-1 min-w-0 flex flex-col items-center px-4 md:px-8 pb-16 ${
            isResizing ? "transition-none select-none" : "transition-all duration-300"
          } ${isDossierOpen ? "xl:mr-[var(--dossier-w)]" : ""}`}
        >
          <div className="w-full max-w-[720px] pt-4">
            <EBookCanvas isFantasy sceneImage={view.sceneImage}>
              <FantasyCombat combat={combat} disabled={!canAct || isNarrating || hasPendingAction} />
              {canAct && (canRest || canClaim) && (
                <div className="flex flex-wrap gap-2 mb-4" aria-label="Available actions">
                  {canRest && <button type="button" disabled={isNarrating || isActionBlocked} onClick={() => submitFantasyAction("rest")} className="min-h-11 px-4 border border-[#80683d] text-[#e6d5b8] disabled:opacity-50">Rest · 5 coins</button>}
                  {canClaim && <button type="button" disabled={isNarrating || isActionBlocked} onClick={() => submitFantasyAction("claim_retrieval_reward")} className="min-h-11 px-4 border border-[#80683d] text-[#e6d5b8] disabled:opacity-50">Claim reward</button>}
                </div>
              )}
              {canAct && (
                <EBookActionDrawer
                  isFantasy
                  actionChips={view.tacticalInclinations}
                  playthroughId={playthrough.playthrough_id}
                  isNarrating={isNarrating || isActionBlocked}
                  canRetry={canRetry}
                  draftInsertion={draft}
                  onSubmit={submitTurn}
                  onContinue={continueTurn}
                  onRetry={retryTurn}
                />
              )}
            </EBookCanvas>
          </div>
        </main>

        {playthrough.mode === "master" && <RulesClipboardContainer />}

        {isDossierOpen && (
          <>
            <button
              type="button"
              onClick={handleCloseDossier}
              aria-label="Close dossier scrim"
              className="fixed inset-0 z-40 bg-black/60 xl:hidden cursor-pointer"
            />
            <div
              ref={panel}
              id="world-dossier"
              className={`fixed right-0 top-[124px] bottom-0 z-40 w-full sm:w-[400px] xl:w-[var(--dossier-w)] shadow-2xl ${
                isResizing ? "transition-none select-none" : "transition-all duration-300"
              }`}
            >
              <FantasyDossierResizer
                sidebarWidth={sidebarWidth}
                minWidth={minSidebarWidth}
                maxWidth={maxSidebarWidth}
                isDragging={isResizing}
                onStartDrag={startResize}
                onKeyDown={handleResizeKeyDown}
              />
              <FantasyDossier
                playthrough={playthrough}
                canTalk={canAct && !isActionBlocked && !isNarrating}
                map={hasMap ? <MapViewer embedded scenarioSnapshot={scenarioSnapshot} state={mapState} /> : undefined}
                mapRequest={mapRequest}
                onClose={handleCloseDossier}
                onTalk={handleTalk}
                onOpenCodex={handleOpenCodex}
              />
            </div>
          </>
        )}
      </div>

      <MemoryDegradedBanner />
      {!canAct && (
        <EBookBottomBar
          isSpectator={playthrough.is_spectator}
          canAct={playthrough.can_act}
          waitingOnLabel={playthrough.next_actor_label}
          isEnded={isEnded}
        />
      )}
      {playthrough.mode === "master" && <PhoneEcho />}
      {isCodexOpen && <EBookCodexDrawer isOpen onClose={toggleCodex} />}
      <ChronicleRecapModal isOpen={isChronicleOpen} onClose={closeChronicle} />
      {degraded && <Toast message={degraded} type="error" onClose={clearDegraded} />}
      {quota && !degraded && <Toast message={quota} type="info" onClose={clearQuota} />}
      {truncated && !degraded && <Toast message={truncated} type="info" onClose={clearTruncated} />}
      {isEnded && playthrough.ended_outcome_tag && (
        <PlaythroughEndedBanner
          outcomeTag={playthrough.ended_outcome_tag}
          outcomeTitle={playthrough.ended_outcome_title ?? "The End"}
          outcomeText={playthrough.ended_outcome_text ?? ""}
          playthroughId={playthrough.playthrough_id}
          onBackToLibrary={() => navigate("/discover")}
        />
      )}
    </div>
  );
}
