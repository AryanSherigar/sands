import type {
  ExpressionOperator,
  FieldExpression,
} from "../components/ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";

const OPERATORS: readonly ExpressionOperator[] = ["==", "!=", "<", "<=", ">", ">=", "in", "contains", "matches"];
const CONNECTIVES = ["AND", "OR", "NOT"] as const;

const isOperator = (value: unknown): value is ExpressionOperator =>
  typeof value === "string" && (OPERATORS as readonly string[]).includes(value);

const isPlainRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isLeafValid = (node: Record<string, unknown>): boolean => {
  if (typeof node.field !== "string" || !isOperator(node.op)) return false;
  const isValueValid = ["undefined", "string", "number", "boolean"].includes(typeof node.value);
  return isValueValid && (node.ref === undefined || typeof node.ref === "string");
};

export const isFieldExpression = (value: unknown): value is FieldExpression => {
  if (!isPlainRecord(value) || !isLeafValid(value)) return false;
  return CONNECTIVES.every((key) => value[key] === undefined || isFieldExpression(value[key]));
};
