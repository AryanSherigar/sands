import { useCallback, useState } from "react";

export function useWarCouncilModals() {
  const [isCodexOpen, setIsCodexOpen] = useState(false);
  const [isRetreatModalOpen, setIsRetreatModalOpen] = useState(false);

  const toggleCodex = useCallback(() => setIsCodexOpen((previous) => !previous), []);
  const toggleRetreatModal = useCallback(
    () => setIsRetreatModalOpen((previous) => !previous),
    [],
  );

  return { isCodexOpen, isRetreatModalOpen, toggleCodex, toggleRetreatModal };
}
