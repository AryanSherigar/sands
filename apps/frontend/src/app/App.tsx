import React from "react";
import { RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";
import { router } from "./router";
import { AuthProvider } from "@/features/auth/providers/AuthProvider";
import { ErrorBoundary } from "@/shared/components/feedback/ErrorBoundary";
import { AlphaCollectionBridge } from "@/shared/components/AlphaCollectionBridge/AlphaCollectionBridge";
import { MatureAttestationDialog } from "@/shared/components/MatureAttestationDialog/MatureAttestationDialog";
import { SignInModal } from "@/shared/components/SignInModal/SignInModal";
import { ToastHost } from "@/shared/components/feedback/ToastHost";
import { queryClient } from "@/shared/lib/query-client";

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <MotionConfig reducedMotion="user">
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <RouterProvider router={router} />
            <SignInModal />
            <MatureAttestationDialog />
            <ToastHost />
            <AlphaCollectionBridge />
          </AuthProvider>
        </QueryClientProvider>
      </MotionConfig>
    </ErrorBoundary>
  );
};
