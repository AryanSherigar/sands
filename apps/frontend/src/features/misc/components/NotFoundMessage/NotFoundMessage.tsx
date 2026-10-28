import React from "react";

export const NotFoundMessage: React.FC = () => {
  return (
    <>
      <p className="font-mono text-xs uppercase tracking-[0.3em] text-accent">
        404
      </p>
      <h1 className="font-display text-3xl text-content">
        This path leads nowhere
      </h1>
      <p className="max-w-sm font-sans text-sm text-content-faint">
        The page you were looking for has wandered off, or never existed.
      </p>
    </>
  );
};
