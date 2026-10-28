import { useMutation, useQueryClient } from "@tanstack/react-query";
import { abandonPlaythrough } from "../api/profileApi";

export const useAbandonPlaythrough = () => {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: abandonPlaythrough,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-playthroughs"] });
      queryClient.invalidateQueries({ queryKey: ["user-profile"] });
      // NOTE: removed rather than invalidated so an inactive Overview cannot
      // flash the abandoned run's Continue card before its refetch lands.
      queryClient.removeQueries({ queryKey: ["profile-overview"] });
    },
  });
};
