import React from "react";
import { Link } from "react-router-dom";

export const Wordmark: React.FC = () => (
  <Link
    to="/"
    className="font-mono text-lg font-semibold lowercase tracking-[0.3em] text-content transition-colors hover:text-accent"
  >
    sands
  </Link>
);
