import React from "react";
import type { FieldBlockProps } from "./Advanced.types";

export const FieldBlock: React.FC<FieldBlockProps> = ({ label, helper, children }) => (
  <div className="space-y-1.5">
    <p className="text-meta font-medium text-content-muted">{label}</p>
    {children}
    {helper && <p className="text-micro text-content-faint">{helper}</p>}
  </div>
);
