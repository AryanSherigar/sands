import React from "react";
import type { TrackedValueFieldsProps } from "./Advanced.types";
import { ChoicesField } from "./ChoicesField";
import { NumberValueFields } from "./NumberValueFields";
import { YesNoField } from "./YesNoField";

export const TrackedValueFields: React.FC<TrackedValueFieldsProps> = (props) => {
  if (props.field.type === "number") return <NumberValueFields {...props} />;
  if (props.field.type === "boolean") return <YesNoField {...props} />;
  return <ChoicesField {...props} />;
};
