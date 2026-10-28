import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { usePlayStore } from "../../stores/play.store";
import { selectCanRetryTurn } from "../../stores/play.selectors";
import { EBookHeader } from "./EBook/EBookHeader";
import { EBookCanvas } from "./EBook/EBookCanvas";
import { EBookBottomBar } from "./EBook/EBookBottomBar";
import { EBookActionDrawer } from "./EBook/EBookActionDrawer";
import { EBookCodexDrawer } from "./EBook/EBookCodexDrawer";
import { ChronicleRecapModal } from "./EBook/ChronicleRecapModal";
import { MemoryDegradedBanner } from "./MemoryDegradedBanner";
import { PlaythroughEndedBanner } from "./PlaythroughEndedBanner";
import { Toast } from "@/shared/components/feedback/Toast";

export function NewbiePlayScreen() {
  const navigate = useNavigate();
  const playthrough = usePlayStore((s) => s.playthrough);
  const theme = usePlayStore((s) => s.ebook_theme);
  const isNarrating = usePlayStore((s) => s.is_narrating);
  const isLeftSidebarOpen = usePlayStore((s) => s.is_left_sidebar_open);
  const isChronicleModalOpen = usePlayStore((s) => s.is_chronicle_modal_open);
  const degradedMessage = usePlayStore((s) => s.degraded_message);
  const quotaNoticeMessage = usePlayStore((s) => s.quota_notice_message);
  const inputTruncatedMessage = usePlayStore(
    (s) => s.input_truncated_message,
  );

  const toggleLeftSidebar = usePlayStore((s) => s.toggleLeftSidebar);
  const setLeftSidebarOpen = usePlayStore((s) => s.setLeftSidebarOpen);
  const openChronicleModal = usePlayStore((s) => s.openChronicleModal);
  const closeChronicleModal = usePlayStore((s) => s.closeChronicleModal);
  const continueTurn = usePlayStore((s) => s.continueTurn);
  const retryLastTurn = usePlayStore((s) => s.retryLastTurn);
  const canRetryTurn = usePlayStore(selectCanRetryTurn);
  const submitTurn = usePlayStore((s) => s.submitTurn);
  const clearDegradedMessage = usePlayStore((s) => s.clearDegradedMessage);
  const clearQuotaNoticeMessage = usePlayStore(
    (s) => s.clearQuotaNoticeMessage,
  );
  const clearInputTruncatedMessage = usePlayStore(
    (s) => s.clearInputTruncatedMessage,
  );

  useEffect(() => {
    setLeftSidebarOpen(false);
  }, [setLeftSidebarOpen]);

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
      {/* Reader Header */}
      <EBookHeader
        onBack={() => navigate("/discover")}
        onOpenCodex={toggleLeftSidebar}
        onOpenChronicle={openChronicleModal}
      />

      {/* Living E-Book Centered Canvas */}
      <div className="relative flex-1 min-h-0 w-full flex justify-center overflow-hidden z-10">
        <EBookCanvas />
      </div>

      {/* Minimal Reader Controls Bottom Dock */}
      <MemoryDegradedBanner />

      {isInputVisible ? (
        <EBookActionDrawer
          onSubmit={submitTurn}
          onContinue={continueTurn}
          onRetry={retryLastTurn}
          canRetry={canRetryTurn}
          isNarrating={isNarrating}
          playthroughId={playthrough.playthrough_id}
        />
      ) : (
        <EBookBottomBar
          isSpectator={playthrough.is_spectator}
          canAct={playthrough.can_act}
          waitingOnLabel={playthrough.next_actor_label}
          isEnded={isEnded}
        />
      )}

      {/* Slide-Over World Codex Drawer */}
      <EBookCodexDrawer
        isOpen={isLeftSidebarOpen}
        onClose={toggleLeftSidebar}
      />

      {/* Post-Game Chronicle Recap Modal */}
      <ChronicleRecapModal
        isOpen={isChronicleModalOpen}
        onClose={closeChronicleModal}
      />

      {/* Degraded Stream Error Toast */}
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
