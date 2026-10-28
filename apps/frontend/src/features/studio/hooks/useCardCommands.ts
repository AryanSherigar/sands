import { useState } from "react";
import { buildDuplicatePayload } from "../lib/cardDraft";
import type { EntityCreate, EntityResponse } from "../types/entity.types";

interface CardCommandsOptions {
  entity: EntityResponse | undefined;
  createEntity: (payload: EntityCreate) => Promise<unknown>;
  deleteEntity: (entityId: string) => Promise<unknown>;
  onDeleted?: (entityId: string) => void;
}

export const useCardCommands = ({
  entity,
  createEntity,
  deleteEntity,
  onDeleted,
}: CardCommandsOptions) => {
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const openDelete = (): void => setIsDeleteOpen(true);
  const closeDelete = (): void => setIsDeleteOpen(false);

  const duplicate = (): void => {
    if (entity) void createEntity(buildDuplicatePayload(entity));
  };

  const confirmDelete = async (): Promise<void> => {
    if (!entity) return;
    setIsDeleting(true);
    try {
      await deleteEntity(entity.entity_id);
      setIsDeleteOpen(false);
      onDeleted?.(entity.entity_id);
    } finally {
      setIsDeleting(false);
    }
  };

  return { isDeleteOpen, isDeleting, openDelete, closeDelete, duplicate, confirmDelete };
};
