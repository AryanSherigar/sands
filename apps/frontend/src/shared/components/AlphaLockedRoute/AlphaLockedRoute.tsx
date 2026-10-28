import React from "react";
import { Navigate } from "react-router-dom";
import { DISCOVER_PATH } from "@/shared/constants/navigation";
import { useAlphaConfig } from "@/shared/hooks/useAlphaConfig";
import type { AlphaLockedRouteProps } from "./AlphaLockedRoute.types";

export const AlphaLockedRoute: React.FC<AlphaLockedRouteProps> = ({
  children,
}) => {
  const { data: config, isPending } = useAlphaConfig();

  if (isPending) return null;
  if (config?.is_alpha_mode) return <Navigate to={DISCOVER_PATH} replace />;

  return <>{children}</>;
};
