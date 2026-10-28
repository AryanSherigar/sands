import { isAxiosError } from "axios";
import React, { useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { acceptScenarioInvite } from "../api/access.api";
import {
  INVITE_ACCEPT_FAILED_MESSAGE,
  INVITE_INVALID_MESSAGE,
  INVITE_USED_MESSAGE,
} from "../constants/invite";

const HTTP_NOT_FOUND = 404;
const HTTP_GONE = 410;
const PAGE_CLASSES =
  "flex min-h-[100dvh] flex-col items-center justify-center gap-4 bg-surface-sunken p-6 text-center font-sans text-body";

const describeFailure = (error: unknown): string => {
  const status = isAxiosError(error) ? error.response?.status : undefined;
  if (status === HTTP_NOT_FOUND) return INVITE_INVALID_MESSAGE;
  if (status === HTTP_GONE) return INVITE_USED_MESSAGE;
  return INVITE_ACCEPT_FAILED_MESSAGE;
};

export const InvitePage: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const hasStartedRef = useRef(false);
  const accept = useMutation({
    mutationFn: (inviteToken: string) => acceptScenarioInvite(inviteToken),
    onSuccess: ({ scenario_id }) => navigate(`/scenario/${scenario_id}`, { replace: true }),
  });
  const { mutate } = accept;

  useEffect(() => {
    if (!token || hasStartedRef.current) return;
    hasStartedRef.current = true;
    mutate(token);
  }, [mutate, token]);

  if (accept.isError || !token) {
    return (
      <div className={PAGE_CLASSES}>
        <p role="alert" className="text-danger">
          {describeFailure(accept.error)}
        </p>
        <Link to="/discover" className="text-content-muted underline underline-offset-4 hover:text-content">
          Browse stories
        </Link>
      </div>
    );
  }

  return <div className={`${PAGE_CLASSES} text-content-muted`}>Opening your invite…</div>;
};
