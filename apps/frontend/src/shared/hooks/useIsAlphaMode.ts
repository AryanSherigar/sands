import { useAlphaConfig } from "./useAlphaConfig";

export function useIsAlphaMode(): boolean {
  const { data } = useAlphaConfig();
  return data?.is_alpha_mode ?? false;
}
