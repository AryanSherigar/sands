export interface FantasyDossierResizerProps {
  sidebarWidth: number;
  minWidth: number;
  maxWidth: number;
  isDragging: boolean;
  onStartDrag: (e: React.MouseEvent | React.TouchEvent) => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
}
