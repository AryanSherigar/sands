import React from "react";
import { Button } from "@/shared/components/ui/Button";
import type { PlaytestMessageProps } from "./PlaytestTab.types";

export const PlaytestMessage: React.FC<PlaytestMessageProps> = ({
  message,
  actionLabel,
  onAction,
  isAlert = false,
}) => (
  <div className="mx-auto flex w-full max-w-[640px] flex-col items-start gap-3 px-4 py-8">
    <p role={isAlert ? "alert" : "status"} className={isAlert ? "text-body text-danger" : "text-body text-content-muted"}>
      {message}
    </p>
    <Button type="button" variant="secondary" onClick={onAction}>
      {actionLabel}
    </Button>
  </div>
);
