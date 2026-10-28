import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";

const NEW_STORY_PATH = "/studio/new";

export const useCreateStory = (): (() => Promise<void>) => {
  const navigate = useNavigate();
  const requireAuth = useRequireAuth("create");

  return useCallback(async (): Promise<void> => {
    if (await requireAuth()) navigate(NEW_STORY_PATH);
  }, [requireAuth, navigate]);
};
