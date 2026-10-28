import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { usePlayStore } from "../../stores/play.store";
import { selectCanRetryTurn } from "../../stores/play.selectors";
import { useHasRulesPanel } from "../../hooks/useHasRulesPanel";
import { CharacterDrawer } from "./EBook/CharacterDrawer";
import { ChronicleRecapModal } from "./EBook/ChronicleRecapModal";
import { EBookActionDrawer } from "./EBook/EBookActionDrawer";
import { EBookBottomBar } from "./EBook/EBookBottomBar";
import { EBookCanvas } from "./EBook/EBookCanvas";
import { EBookCodexDrawer } from "./EBook/EBookCodexDrawer";
import { EBookHeader } from "./EBook/EBookHeader";
import { RulesClipboardContainer } from "../RulesClipboard/RulesClipboardContainer";
import { MemoryDegradedBanner } from "./MemoryDegradedBanner";
import { PlaythroughEndedBanner } from "./PlaythroughEndedBanner";
import { PhoneEcho } from "../PhoneEcho/PhoneEcho";
import { Toast } from "@/shared/components/feedback/Toast";

export function MasterPlayScreen() {
  const navigate = useNavigate();
  const playthrough = usePlayStore((s) => s.playthrough);
  const theme = usePlayStore((s) => s.ebook_theme);
  const isNarrating = usePlayStore((s) => s.is_narrating);
  const isLeftSidebarOpen = usePlayStore((s) => s.is_left_sidebar_open);
  const isCharacterDrawerOpen = usePlayStore((s) => s.is_right_sidebar_open);
  const isChronicleModalOpen = usePlayStore((s) => s.is_chronicle_modal_open);
  const degradedMessage = usePlayStore((s) => s.degraded_message);
  const quotaNoticeMessage = usePlayStore((s) => s.quota_notice_message);
  const inputTruncatedMessage = usePlayStore(
    (s) => s.input_truncated_message,
  );

  const toggleLeftSidebar = usePlayStore((s) => s.toggleLeftSidebar);
  const setLeftSidebarOpen = usePlayStore((s) => s.setLeftSidebarOpen);
  const toggleRightSidebar = usePlayStore((s) => s.toggleRightSidebar);
  const setRightSidebarOpen = usePlayStore((s) => s.setRightSidebarOpen);
  const openChronicleModal = usePlayStore((s) => s.openChronicleModal);
  const closeChronicleModal = usePlayStore((s) => s.closeChronicleModal);
  const continueTurn = usePlayStore((s) => s.continueTurn);
  const retryLastTurn = usePlayStore((s) => s.retryLastTurn);
  const canRetryTurn = usePlayStore(selectCanRetryTurn);
  const hasRulesPanel = useHasRulesPanel();
  const isRulesPanelHidden = usePlayStore((s) => s.is_rules_panel_hidden);
  const submitTurn = usePlayStore((s) => s.submitTurn);
  const clearDegradedMessage = usePlayStore((s) => s.clearDegradedMessage);
  const clearQuotaNoticeMessage = usePlayStore(
    (s) => s.clearQuotaNoticeMessage,
  );
  const clearInputTruncatedMessage = usePlayStore(
    (s) => s.clearInputTruncatedMessage,
  );

  // NOTE: Both drawers stay closed by default, matching NewbiePlayScreen's clean
  // reading-first shell.
  useEffect(() => {
    setLeftSidebarOpen(false);
    setRightSidebarOpen(false);
  }, [setLeftSidebarOpen, setRightSidebarOpen]);

  if (!playthrough) return null;

  const isEnded = Boolean(playthrough.ended_outcome_tag);
  const isInputVisible =
    !isEnded && !playthrough.is_spectator && playthrough.can_act;
  const isSepia = theme === "antique-sepia";
  const containerTheme = isSepia
    ? "bg-[#f4ebd9] text-[#2c2217] selection:bg-[#e2d5be]"
    : "bg-surface-sunken text-content selection:bg-surface-raised selection:text-content";

  return (
    <div
      className={`relative min-h-dvh h-dvh w-full flex flex-col overflow-hidden font-sans transition-colors ${containerTheme}`}
    >
      <EBookHeader
        onBack={() => navigate("/discover")}
        onOpenCodex={toggleLeftSidebar}
        onOpenChronicle={openChronicleModal}
      />

      <div className="relative flex-1 min-h-0 w-full flex overflow-hidden z-10">
        <div className="flex min-w-0 flex-1 justify-center overflow-hidden">
          <EBookCanvas />
        </div>
        <RulesClipboardContainer />
      </div>

      <MemoryDegradedBanner />

      {isInputVisible ? (
        <EBookActionDrawer
          onSubmit={submitTurn}
          onContinue={continueTurn}
          onRetry={retryLastTurn}
          canRetry={canRetryTurn}
          isNarrating={isNarrating}
          playthroughId={playthrough.playthrough_id}
          actionChips={playthrough.action_chips}
        />
      ) : (
        <EBookBottomBar
          isSpectator={playthrough.is_spectator}
          canAct={playthrough.can_act}
          waitingOnLabel={playthrough.next_actor_label}
          isEnded={isEnded}
          hasRulesPanel={hasRulesPanel && !isRulesPanelHidden}
        />
      )}

      <PhoneEcho />

      <EBookCodexDrawer
        isOpen={isLeftSidebarOpen}
        onClose={toggleLeftSidebar}
      />

      <CharacterDrawer
        isOpen={isCharacterDrawerOpen}
        onClose={toggleRightSidebar}
        playerStats={playthrough.player_stats}
        playerInventory={playthrough.player_inventory}
        entities={playthrough.entities}
        objectives={playthrough.objectives}
      />

      <ChronicleRecapModal
        isOpen={isChronicleModalOpen}
        onClose={closeChronicleModal}
      />

      {degradedMessage && (
        <Toast
          message={degradedMessage}
          type="error"
          onClose={clearDegradedMessage}
        />
      )}
      {quotaNoticeMessage && !degradedMessage && (
        <Toast
          message={quotaNoticeMessage}
          type="info"
          onClose={clearQuotaNoticeMessage}
        />
      )}
      {inputTruncatedMessage && !degradedMessage && (
        <Toast
          message={inputTruncatedMessage}
          type="info"
          onClose={clearInputTruncatedMessage}
        />
      )}

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
