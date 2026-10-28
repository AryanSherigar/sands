import type {
  StateMutation,
  StateMutationOp,
} from "@/shared/types/stateMutation.types";

export const MAX_MUTATIONS_PER_LIST = 16;

export const MUTATION_OP_OPTIONS: { value: StateMutationOp; label: string }[] =
  [
    { value: "set", label: "set" },
    { value: "increment", label: "increment" },
    { value: "decrement", label: "decrement" },
  ];

export const buildEmptyMutation = (): StateMutation => ({
  path: "",
  op: "set",
  value: "",
});
