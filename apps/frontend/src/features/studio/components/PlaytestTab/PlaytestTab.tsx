import React from "react";
import { PLAYTEST_NO_OPENING_MESSAGE } from "../../constants/playtest";
import { GUIDE_TAB_ID } from "../../constants/studioTabs";
import { usePlaytestTab } from "../../hooks/usePlaytestTab";
import { usePlaytestTurns } from "../../hooks/usePlaytestTurns";
import { usePlaytestStore } from "../../stores/playtest.store";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { PlaytestActionBox } from "./PlaytestActionBox";
import { PlaytestMessage } from "./PlaytestMessage";
import { PlaytestSetupForm } from "./PlaytestSetupForm";
import { PlaytestStaleBanner } from "./PlaytestStaleBanner";
import { PlaytestToolbar } from "./PlaytestToolbar";
import { StateReadout } from "./StateReadout";
import { PlaytestTranscript } from "./PlaytestTranscript";

const OPENING_STEP_NUMBER = 6;
const CENTERED_STATUS_CLASSES = "px-4 py-8 text-center text-body text-content-muted";

export const PlaytestTab: React.FC = () => {
  const turns = usePlaytestTurns();
  const tab = usePlaytestTab(turns.cancelTurn);
  const openingText = usePlaytestStore((state) => state.openingText);
  const sessionTurns = usePlaytestStore((state) => state.turns);
  const testNote = usePlaytestStore((state) => state.note);

  const handleGoToOpening = (): void => {
    const store = useStudioTabsStore.getState();
    store.focusTab(GUIDE_TAB_ID);
    store.setGuideView("steps");
    store.setGuideStep(OPENING_STEP_NUMBER);
  };

  if (tab.startError) {
    return <PlaytestMessage isAlert message={tab.startError} actionLabel="Try again" onAction={tab.retryStart} />;
  }
  if (!tab.hasSession && !tab.hasOpening) {
    return (
      <PlaytestMessage
        message={PLAYTEST_NO_OPENING_MESSAGE}
        actionLabel="Go to Opening"
        onAction={handleGoToOpening}
      />
    );
  }
  if (!tab.hasSession && tab.needsForm) {
    return <PlaytestSetupForm fields={tab.setupFields} isStarting={tab.isStarting} onStart={tab.start} />;
  }
  if (!tab.hasSession) {
    return <p role="status" className={CENTERED_STATUS_CLASSES}>Starting your playtest…</p>;
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <PlaytestToolbar isBusy={tab.isStarting} onRestart={tab.restart} onEnd={tab.end} />
      {tab.isStale && <PlaytestStaleBanner onKeepPlaying={tab.keepPlaying} />}
      <StateReadout />
      {testNote && <p role="status" className="px-4 py-2 text-meta text-content-muted">{testNote}</p>}
      <div className="min-h-0 flex-1 overflow-y-auto">
        <PlaytestTranscript
          openingText={openingText}
          turns={sessionTurns}
          streamingNarration={turns.narration}
          isStreaming={turns.isStreaming}
        />
      </div>
      {turns.notice && <p role="status" className="px-4 text-meta text-content-muted">{turns.notice}</p>}
      {turns.failureMessage && (
        <div className="flex items-center gap-3 px-4 py-2">
          <p role="alert" className="text-meta text-danger">{turns.failureMessage}</p>
          <button type="button" onClick={turns.retryAction} className="text-meta text-content underline underline-offset-4">
            Try again
          </button>
        </div>
      )}
      <PlaytestActionBox isDisabled={turns.isStreaming || tab.isStarting} onSubmit={turns.submitAction} />
    </div>
  );
};
