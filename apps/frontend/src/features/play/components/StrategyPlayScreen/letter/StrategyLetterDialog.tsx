import React from "react";
import type { StrategyLetterDialogProps } from "./StrategyLetterDialog.types";
import { useLetterScene } from "../../../hooks/useLetterScene";
import { LetterAmbientCanopy } from "./LetterAmbientCanopy";
import { LetterPouchStage } from "./pouch/LetterPouchStage";
import { LetterDraftingStage } from "./drafting/LetterDraftingStage";
import type {
  LetterSealHandler,
  LetterStage,
  ScribeDraftRequester,
  StrategyLetterPackage,
} from "../../../types/letterScene.types";

function renderLetterStage(
  stage: LetterStage,
  pkg: StrategyLetterPackage,
  scene: ReturnType<typeof useLetterScene>
) {
  if (stage === "reading") {
    return (
      <LetterPouchStage pkg={pkg} onSelectDocket={scene.handleSelectDocket} />
    );
  }
  return (
    <LetterDraftingStage
      pkg={pkg}
      activeDraft={scene.activeDraft}
      mode={scene.mode}
      canUndo={scene.canUndo}
      canRedo={scene.canRedo}
      isSealing={scene.isSealing}
      onRewrite={scene.handleScribeRewrite}
      onUpdateBody={scene.handleUpdateBody}
      onUndo={scene.handleUndo}
      onRedo={scene.handleRedo}
      onDiscard={() => scene.handleSelectDocket("aside")}
      onSealAndSend={scene.handleSealAndSend}
    />
  );
}

function StrategyLetterDialogContent({
  pkg,
  onSeal,
  onClose,
  onRequestScribeDraft,
  onDecline,
}: {
  pkg: StrategyLetterPackage;
  onSeal?: LetterSealHandler;
  onClose?: () => void;
  onRequestScribeDraft?: ScribeDraftRequester;
  onDecline?: () => void;
}) {
  const scene = useLetterScene(pkg, onSeal, onClose, onRequestScribeDraft, onDecline);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Courier Letter Dispatch"
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-parchment-base/40 backdrop-blur-md p-3 sm:p-5 md:p-6"
    >
      <div className="relative w-full max-w-[1440px] flex flex-col justify-start">
        {scene.stage === "reading" && (
          <LetterAmbientCanopy
            stage={scene.stage}
            dispatchNumber={pkg.dispatchNumber}
            dateSolar={pkg.incoming.dateSolar}
            isMuted={scene.isMuted}
            onReturnToDesk={() => scene.handleSelectDocket("aside")}
            onToggleMute={scene.handleToggleMute}
          />
        )}
        {renderLetterStage(scene.stage, pkg, scene)}
        {scene.toastMessage && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg bg-surface-container text-on-surface font-display text-body-sm italic shadow-lg border border-on-surface/20">
            {scene.toastMessage}
          </div>
        )}
      </div>
    </div>
  );
}

export const StrategyLetterDialog: React.FC<StrategyLetterDialogProps> = ({
  isOpen,
  pkg,
  onSeal,
  onClose,
  onRequestScribeDraft,
  onDecline,
}) => {
  if (!isOpen) return null;
  return (
    <StrategyLetterDialogContent
      pkg={pkg}
      onSeal={onSeal}
      onClose={onClose}
      onRequestScribeDraft={onRequestScribeDraft}
      onDecline={onDecline}
    />
  );
};
