import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/shared/hooks/useToast";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { buildPlaytestSetupPath } from "@/shared/constants/navigation";
import { startPlaytest as requestPlaytest } from "@/shared/api/playthroughs.api";

const PLAYTEST_FAILED_MESSAGE = "Couldn't start the playtest.";

export const useStartPlaytest = (
  scenarioId: string,
  hasSetupFields: boolean,
) => {
  const navigate = useNavigate();
  const showToast = useToast();

  const mutation = useMutation({
    mutationFn: () => requestPlaytest(scenarioId),
    onSuccess: (playthrough) => navigate(`/play/${playthrough.playthrough_id}`),
    onError: (error) =>
      showToast(extractErrorMessage(error, PLAYTEST_FAILED_MESSAGE), "error"),
  });

  const startPlaytest = (): void => {
    if (hasSetupFields) {
      navigate(buildPlaytestSetupPath(scenarioId));
      return;
    }
    mutation.mutate();
  };

  return {
    startPlaytest,
    isStartingPlaytest: mutation.isPending,
  };
};
