import React from "react";
import { Link } from "react-router-dom";
import { IconAlertTriangle } from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import type { MatureGateProps } from "./MatureGate.types";

export const MatureGate: React.FC<MatureGateProps> = ({ onShowAnyway }) => (
  <section
    aria-labelledby="scenario-mature-heading"
    className="mx-auto flex max-w-md flex-col items-center gap-4 rounded-md border border-border-strong bg-surface-raised p-8 text-center"
  >
    <IconAlertTriangle size={28} stroke={1.5} className="text-danger" aria-hidden="true" />
    <h2
      id="scenario-mature-heading"
      className="font-display text-xl font-bold text-content"
    >
      This story is marked mature
    </h2>
    <p className="font-sans text-sm text-content-muted">
      It may include graphic violence, strong language or other content meant
      for adults.
    </p>
    <Button type="button" onClick={onShowAnyway}>
      Show anyway
    </Button>
    <Link
      to="/settings"
      className="font-sans text-xs text-content-faint underline underline-offset-4 hover:text-content"
    >
      Change in Settings
    </Link>
  </section>
);
