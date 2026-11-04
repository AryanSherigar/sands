import { useQuery } from "@tanstack/react-query";
import { listPremadeAvatars } from "../api/avatarStudio.api";

const PREMADE_AVATARS_STALE_TIME_MS = 5 * 60_000;

export const usePremadeAvatars = () =>
  useQuery({
    queryKey: ["studio", "premade-avatars"],
    queryFn: listPremadeAvatars,
    staleTime: PREMADE_AVATARS_STALE_TIME_MS,
  });
