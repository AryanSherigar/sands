import type { FieldExpression } from "../components/ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import { COMPARISON_DESCRIPTIONS, COMPARISON_OPERATORS } from "../constants/comparisons";
import type {
  Comparison,
  Sentence,
  SentenceJoiner,
  SentenceMetadata,
  SentenceRow,
  WhileLimit,
} from "../types/sentence.types";

type ChainConnective = "AND" | "OR";
type ExpressionValue = FieldExpression["value"];

interface ChainLink {
  joiner: SentenceJoiner;
  next: FieldExpression;
}

const CONNECTIVE_KEYS = ["AND", "OR", "NOT"] as const;

const JOINER_CONNECTIVE: Record<SentenceJoiner, ChainConnective> = {
  and: "AND",
  or: "OR",
};

const REF_COMPARISONS: Partial<Record<FieldExpression["op"], Comparison>> = {
  "<=": "at_most",
  ">=": "at_least",
  "==": "exactly",
};

const HINT_FAMILIES: Partial<Record<Comparison, readonly Comparison[]>> = {
  at_most: ["at_most", "drops_to"],
  at_least: ["at_least", "rises_to"],
};

const compileRow = (row: SentenceRow): FieldExpression => {
  const base = { field: row.path, op: COMPARISON_OPERATORS[row.comparison] };
  if (row.ref !== undefined) return { ...base, ref: row.ref };
  if (row.comparison === "becomes_yes") return { ...base, value: true };
  if (row.comparison === "becomes_no") return { ...base, value: false };
  return row.amount === undefined ? base : { ...base, value: row.amount };
};

export const compileSentence = ({ rows, joiner }: Sentence): FieldExpression => {
  if (rows.length === 0) throw new Error("A sentence needs at least one row.");
  const connective = JOINER_CONNECTIVE[joiner];
  const last = compileRow(rows[rows.length - 1]);
  return rows
    .slice(0, -1)
    .reduceRight<FieldExpression>((tail, row) => ({ ...compileRow(row), [connective]: tail }), last);
};

export const buildSentenceMetadata = ({ rows, joiner }: Sentence): SentenceMetadata => ({
  rows: rows.map((row) => ({ comparison: row.comparison })),
  joiner,
});

const equalityComparison = (value: ExpressionValue): Comparison | null => {
  if (value === true) return "becomes_yes";
  if (value === false) return "becomes_no";
  if (typeof value === "number") return "exactly";
  if (typeof value === "string") return "becomes_option";
  return null;
};

const canonicalComparison = (leaf: FieldExpression): Comparison | null => {
  if (leaf.ref !== undefined) return REF_COMPARISONS[leaf.op] ?? null;
  if (leaf.op === "==") return equalityComparison(leaf.value);
  if (typeof leaf.value !== "number") return null;
  if (leaf.op === "<=") return "at_most";
  if (leaf.op === ">=") return "at_least";
  return null;
};

const restoreComparison = (canonical: Comparison, hint: Comparison | undefined): Comparison =>
  hint && HINT_FAMILIES[canonical]?.includes(hint) ? hint : canonical;

const hasConnective = (node: FieldExpression): boolean =>
  CONNECTIVE_KEYS.some((key) => node[key] !== undefined);

const readAmount = (leaf: FieldExpression, comparison: Comparison): Partial<SentenceRow> => {
  if (leaf.ref !== undefined) return { ref: leaf.ref };
  if (comparison === "becomes_yes" || comparison === "becomes_no") return {};
  return { amount: leaf.value as number | string };
};

const parseLeaf = (leaf: FieldExpression, hint?: Comparison): SentenceRow | null => {
  if (typeof leaf.field !== "string") return null;
  const canonical = canonicalComparison(leaf);
  if (canonical === null) return null;
  const comparison = restoreComparison(canonical, hint);
  return { path: leaf.field, comparison, ...readAmount(leaf, comparison) };
};

const readLink = (node: FieldExpression): ChainLink | "end" | null => {
  const present = CONNECTIVE_KEYS.filter((key) => node[key] !== undefined);
  if (present.length === 0) return "end";
  if (present.length > 1 || node.NOT !== undefined) return null;
  const isAnd = node.AND !== undefined;
  return { joiner: isAnd ? "and" : "or", next: (isAnd ? node.AND : node.OR) as FieldExpression };
};

const collectChain = (
  expression: FieldExpression,
): { nodes: FieldExpression[]; joiners: SentenceJoiner[] } | null => {
  const nodes: FieldExpression[] = [];
  const joiners: SentenceJoiner[] = [];
  let current: FieldExpression | null = expression;
  while (current) {
    nodes.push(current);
    const link = readLink(current);
    if (link === null) return null;
    if (link === "end") break;
    joiners.push(link.joiner);
    current = link.next;
  }
  return { nodes, joiners };
};

export const parseExpression = (
  expression: FieldExpression,
  metadata?: SentenceMetadata,
): Sentence | null => {
  const chain = collectChain(expression);
  if (chain === null || new Set(chain.joiners).size > 1) return null;
  const rows = chain.nodes.map((node, index) => parseLeaf(node, metadata?.rows[index]?.comparison));
  if (rows.some((row) => row === null)) return null;
  return { rows: rows as SentenceRow[], joiner: chain.joiners[0] ?? metadata?.joiner ?? "and" };
};

export const compileWhileLimit = (guard: SentenceRow, must: SentenceRow): FieldExpression => {
  // NOTE: a node holding only NOT evaluates to "not sub" in expression_evaluator.py,
  // which has no field/op, so the shared FieldExpression type cannot express it.
  const negatedGuard = { NOT: compileRow(guard) } as unknown as FieldExpression;
  return { ...compileRow(must), OR: negatedGuard };
};

const isNegationOnly = (node: FieldExpression | undefined): node is FieldExpression =>
  node !== undefined &&
  typeof node.field !== "string" &&
  node.NOT !== undefined &&
  node.AND === undefined &&
  node.OR === undefined;

export const parseWhileLimit = (
  expression: FieldExpression,
  metadata?: SentenceMetadata,
): WhileLimit | null => {
  if (expression.AND !== undefined || expression.NOT !== undefined) return null;
  if (!isNegationOnly(expression.OR)) return null;
  const guardNode = expression.OR.NOT as FieldExpression;
  if (hasConnective(guardNode)) return null;
  const guard = parseLeaf(guardNode, metadata?.rows[0]?.comparison);
  const must = parseLeaf(expression, metadata?.rows[1]?.comparison);
  return guard && must ? { guard, must } : null;
};

const describeAmount = (row: SentenceRow, labels: Record<string, string>): string | null => {
  if (row.ref !== undefined) return labels[row.ref] ?? row.ref;
  return row.amount === undefined ? null : String(row.amount);
};

const describeRow = (row: SentenceRow, labels: Record<string, string>): string => {
  const parts = [labels[row.path] ?? row.path, COMPARISON_DESCRIPTIONS[row.comparison]];
  const amount = describeAmount(row, labels);
  return (amount === null ? parts : [...parts, amount]).join(" ");
};

export const describeSentence = (sentence: Sentence, labels: Record<string, string>): string =>
  sentence.rows.map((row) => describeRow(row, labels)).join(` ${sentence.joiner} `);

export const describeWhileLimit = ({ guard, must }: WhileLimit, labels: Record<string, string>): string => {
  const describeOne = (row: SentenceRow): string => describeSentence({ rows: [row], joiner: "and" }, labels);
  return `While ${describeOne(guard)}, always ${describeOne(must)}`;
};
