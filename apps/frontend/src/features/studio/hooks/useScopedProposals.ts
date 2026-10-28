import { useCallback, useState } from "react";
import { logEvent } from "@/shared/lib/logger";
import type { ActionBlock, ConflictModalState } from "../types/assistant.types";
import type {
  ScopedProposalState,
  ScopedTabBinding,
  ScopedWriteMode,
} from "../types/scopedChat.types";

const CLOSED_CONFLICT: ConflictModalState = {
  isOpen: false,
  target: "lore",
  targetLabel: "",
  existingValue: "",
  newValue: "",
};

const WRITE_FAILED_MESSAGE = "Couldn't apply that suggestion. Try again.";

interface PendingConflict {
  block: ActionBlock;
  key: string;
}

export const useScopedProposals = (
  binding: ScopedTabBinding | undefined,
  reportError: (message: string) => void,
) => {
  const [stateByKey, setStateByKey] = useState<Record<string, ScopedProposalState>>({});
  const [conflict, setConflict] = useState<ConflictModalState>(CLOSED_CONFLICT);
  const [pending, setPending] = useState<PendingConflict | null>(null);

  const setProposalState = useCallback((key: string, next: ScopedProposalState): void => {
    setStateByKey((previous) => ({ ...previous, [key]: next }));
  }, []);

  const write = useCallback(
    async (block: ActionBlock, key: string, mode: ScopedWriteMode): Promise<void> => {
      if (!binding) return;
      try {
        await binding.applyProposal(block, mode);
        setProposalState(key, "applied");
      } catch (error) {
        logEvent("warning", "scoped_chat_apply_failed", { message: String(error) });
        reportError(WRITE_FAILED_MESSAGE);
      }
    },
    [binding, reportError, setProposalState],
  );

  const accept = useCallback(
    (block: ActionBlock, key: string, shownBefore: string): void => {
      if (!binding) return;
      const live = binding.describeProposal(block);
      if (!live.canApply) return;
      if (live.before === shownBefore) {
        void write(block, key, "replace");
        return;
      }
      setPending({ block, key });
      setConflict({
        isOpen: true,
        target: block.target,
        targetLabel: live.label,
        existingValue: live.before,
        newValue: block.content,
      });
    },
    [binding, write],
  );

  const resolveConflict = useCallback(
    (mode: ScopedWriteMode): void => {
      const current = pending;
      setPending(null);
      setConflict(CLOSED_CONFLICT);
      if (current) void write(current.block, current.key, mode);
    },
    [pending, write],
  );

  const closeConflict = useCallback((): void => {
    setPending(null);
    setConflict(CLOSED_CONFLICT);
  }, []);

  const dismiss = useCallback(
    (key: string): void => setProposalState(key, "dismissed"),
    [setProposalState],
  );

  return { stateByKey, conflict, accept, dismiss, resolveConflict, closeConflict };
};
