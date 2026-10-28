import { StateMutation } from "@/shared/types/stateMutation.types";

export interface StateMutationRowProps {
  index: number;
  total: number;
  mutation: StateMutation;
  onChange: (index: number, mutation: StateMutation) => void;
  onMove: (index: number, offset: number) => void;
  onRemove: (index: number) => void;
}
