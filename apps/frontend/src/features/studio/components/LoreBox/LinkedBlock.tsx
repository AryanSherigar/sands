import React from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { IconAlertTriangle, IconGripVertical } from "@tabler/icons-react";
import { OverflowMenu } from "@/shared/components/ui/OverflowMenu";
import type { OverflowMenuItem } from "@/shared/components/ui/OverflowMenu.types";
import { LORE_BLOCK_ID_PREFIX } from "../../constants/loreBox";
import { getTextareaRows } from "../../lib/loreBoxLayout";
import { renderBlockLine } from "../../lib/loreDocument";
import type { LinkedBlockProps } from "./LoreBox.types";

const TEXT_BLOCK_NAME = "Note";

export const LinkedBlock: React.FC<LinkedBlockProps> = ({
  block,
  index,
  canMoveUp,
  canMoveDown,
  isPicked,
  isMissing,
  onEdit,
  onRemove,
  onUnlink,
  onMove,
  onAddToAlwaysRemember,
}) => {
  const isAnswer = block.kind === "answer";
  const name = block.label || TEXT_BLOCK_NAME;
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: `${LORE_BLOCK_ID_PREFIX}${index}`, disabled: !isAnswer });

  const menuItems: OverflowMenuItem[] = [];
  if (onAddToAlwaysRemember && block.text.trim()) {
    menuItems.push({
      id: "always-remember",
      label: "Add to Always remember",
      onSelect: () => onAddToAlwaysRemember(renderBlockLine(block)),
    });
  }
  if (isAnswer && !isPicked) {
    menuItems.push({ id: "unlink", label: "Unlink", onSelect: () => onUnlink(index) });
  }
  if (canMoveUp) {
    menuItems.push({ id: "up", label: "Move up", onSelect: () => onMove(index, -1) });
  }
  if (canMoveDown) {
    menuItems.push({ id: "down", label: "Move down", onSelect: () => onMove(index, 1) });
  }
  menuItems.push({
    id: "delete",
    label: "Delete",
    isDanger: true,
    onSelect: () => onRemove(index),
  });

  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>): void =>
    onEdit(index, event.target.value);

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className="rounded-md border border-border-subtle bg-surface-inset p-3"
    >
      <div className="mb-2 flex items-center gap-2">
        {isAnswer && (
          <button
            type="button"
            aria-label={`Drag ${name} to reorder`}
            className="cursor-grab text-content-faint hover:text-content-muted"
            {...attributes}
            {...listeners}
          >
            <IconGripVertical size={16} aria-hidden="true" />
          </button>
        )}
        {isAnswer && (
          <span className="text-meta font-medium text-content-muted">{name} ↔</span>
        )}
        <div className="ml-auto">
          <OverflowMenu label={`${name} options`} items={menuItems} />
        </div>
      </div>
      {isMissing && (
        <p className="flex items-center gap-2 text-meta text-warning">
          <IconAlertTriangle size={14} aria-hidden="true" />
          Missing: {block.text}
        </p>
      )}
      {!isMissing && isPicked && (
        <p className="text-base leading-relaxed text-content">{block.text}</p>
      )}
      {!isMissing && !isPicked && (
        <textarea
          aria-label={name}
          value={block.text}
          rows={getTextareaRows(block.text)}
          onChange={handleChange}
          className="w-full resize-y rounded-sm bg-transparent text-base leading-relaxed text-content placeholder:text-content-faint focus:outline-hidden"
        />
      )}
    </div>
  );
};
