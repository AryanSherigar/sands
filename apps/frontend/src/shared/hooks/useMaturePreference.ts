import { useCallback, useState } from "react";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { updateMaturePreference } from "@/shared/api/userPreferences.api";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { useMatureAttestationStore } from "@/shared/stores/matureAttestation.store";

const SAVE_FAILED_MESSAGE = "Couldn't save your content preference.";

export interface MatureChangeResult {
  isApplied: boolean;
  errorMessage: string | null;
}

const DECLINED_RESULT: MatureChangeResult = {
  isApplied: false,
  errorMessage: null,
};

export const useMaturePreference = () => {
  const isEnabled = useAuthStore((state) => Boolean(state.user?.show_mature));
  const patchUser = useAuthStore((state) => state.patchUser);
  const requestAttestation = useMatureAttestationStore(
    (state) => state.request,
  );
  const [isSaving, setIsSaving] = useState(false);

  const setEnabled = useCallback(
    async (next: boolean): Promise<MatureChangeResult> => {
      if (next && !(await requestAttestation())) return DECLINED_RESULT;
      setIsSaving(true);
      try {
        const saved = await updateMaturePreference(next);
        patchUser({ show_mature: saved.show_mature });
        return { isApplied: true, errorMessage: null };
      } catch (error) {
        return {
          isApplied: false,
          errorMessage: extractErrorMessage(error, SAVE_FAILED_MESSAGE),
        };
      } finally {
        setIsSaving(false);
      }
    },
    [patchUser, requestAttestation],
  );

  return { isEnabled, isSaving, setEnabled };
};
