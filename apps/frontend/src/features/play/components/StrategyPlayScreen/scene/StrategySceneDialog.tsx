import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { AI_INITIATOR, NEGOTIATION_SCENE_TYPE } from "../../../constants/scene.constants";
import { useSceneDialog } from "../../../hooks/useSceneDialog";
import { SceneComposer } from "./SceneComposer";
import { SceneOutcomeBanner } from "./SceneOutcomeBanner";
import { SceneTermsCard } from "./SceneTermsCard";
import { SceneTranscript } from "./SceneTranscript";
import type { StrategySceneDialogProps } from "./StrategySceneDialog.types";

export const StrategySceneDialog: React.FC<StrategySceneDialogProps> = ({
  playthroughId,
  sceneId,
  onClose,
}) => {
  const { scene, isFinished, isBusy, stream, decision } = useSceneDialog(
    playthroughId,
    sceneId,
  );

  if (!scene || scene.scene_type !== NEGOTIATION_SCENE_TYPE) return null;

  const leaderName = scene.participants[0]?.name ?? "The ruler";
  const errorMessage = stream.failureMessage ?? decision.errorMessage;
  const handleLeave = (): void => decision.decide({ isConfirmed: false });
  const handleSign = (): void =>
    decision.decide({
      isConfirmed: true,
      proposalSequence: scene.pending_proposal_sequence ?? undefined,
    });
  const isDeclinable = scene.is_declinable !== false;
  const isOffer = scene.initiator === AI_INITIATOR;

  return (
    <Modal isOpen onClose={onClose} title={leaderName} isDismissible={isFinished}>
      <div className="flex flex-col gap-3">
        {isOffer ? (
          <span className="text-micro font-semibold uppercase tracking-wide text-accent">
            Incoming offer
          </span>
        ) : null}
        <p className="text-sm text-content-muted">{scene.situation.summary}</p>
        <SceneTranscript
          exchanges={scene.transcript}
          leaderName={leaderName}
          pendingPlayerText={stream.pendingPlayerText}
          streamingReply={stream.reply}
        />
        {errorMessage ? (
          <p role="alert" className="text-sm text-danger">
            {errorMessage}
          </p>
        ) : null}
        {isFinished ? (
          <SceneOutcomeBanner outcome={scene.outcome} onClose={onClose} />
        ) : (
          <>
            {scene.pending_proposal ? (
              <SceneTermsCard
                card={scene.pending_proposal}
                isBusy={isBusy}
                onConfirm={handleSign}
                counterpartName={leaderName}
                currentTurn={scene.turn}
                onDecline={isDeclinable ? handleLeave : undefined}
              />
            ) : null}
            <SceneComposer
              isDisabled={isBusy}
              exchangesRemaining={scene.exchanges_remaining}
              onSend={stream.sendMessage}
            />
            {isDeclinable ? (
              <Button variant="ghost" size="sm" disabled={isBusy} onClick={handleLeave}>
                Leave the table
              </Button>
            ) : null}
          </>
        )}
      </div>
    </Modal>
  );
};
