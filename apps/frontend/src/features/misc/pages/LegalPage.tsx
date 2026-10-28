import React from "react";
import { Link } from "react-router-dom";
import { ALPHA_DATA_NOTICE } from "@/shared/constants/alpha-data-notice";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";

export interface LegalPageProps {
  title: string;
  children: React.ReactNode;
}

export const LegalPage: React.FC<LegalPageProps> = ({ title, children }) => {
  const isAlphaMode = useIsAlphaMode();

  return (
    <main className="mx-auto min-h-dvh max-w-2xl bg-surface px-6 py-20 text-content">
      <Link
        to="/"
        className="font-mono text-sm font-semibold lowercase tracking-[0.3em] text-content-muted transition-colors hover:text-content"
      >
        sands
      </Link>
      <h1 className="mt-8 font-display text-3xl text-content">{title}</h1>
      <div className="mt-6 space-y-4 font-sans text-sm leading-relaxed text-content-muted">
        {isAlphaMode && <p className="text-content">{ALPHA_DATA_NOTICE}</p>}
        {children}
      </div>
    </main>
  );
};
