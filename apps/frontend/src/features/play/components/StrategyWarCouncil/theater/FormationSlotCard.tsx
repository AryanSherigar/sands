export interface FormationSlotCardProps {
  slot: "left" | "center" | "right";
  title: string;
  unitName: string;
  troopCountText: string;
  morale: number;
  isAnchor: boolean;
  onSelect: () => void;
}

export function FormationSlotCard({
  title,
  unitName,
  troopCountText,
  morale,
  isAnchor,
  onSelect,
}: FormationSlotCardProps) {
  return (
    <div
      onClick={onSelect}
      className={`formation-slot relative p-3 rounded-xl bg-[#F7F0DC]/90 backdrop-blur-md shadow-md cursor-pointer transition border ${
        isAnchor
          ? "border-[#D2A94A]/40 ring-2 ring-[#D2A94A] -translate-y-2 bg-[#F7F0DC]"
          : "border-[#3A3128]/10 hover:bg-[#F7F0DC]"
      }`}
    >
      {isAnchor && (
        <span className="anchor-badge absolute -top-3 left-1/2 -translate-x-1/2 px-2.5 py-0.5 rounded-full bg-[#785a00] text-white text-[10px] tracking-wider uppercase shadow-sm whitespace-nowrap font-semibold">
          Tactic Anchor
        </span>
      )}
      <div className="flex items-center justify-between mb-1.5">
        <span className={`text-[10px] uppercase tracking-wider ${isAnchor ? "text-[#785a00] font-semibold" : "text-[#42474b]"}`}>
          {title}
        </span>
        <span className="material-symbols-outlined text-[16px] text-[#5E8A5A]">
          {isAnchor ? "shield" : "front_hand"}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-9 h-9 rounded-lg bg-[#fbebde] flex items-center justify-center text-[#2e4856] shadow-inner shrink-0">
          <span className="material-symbols-outlined text-[20px]">groups</span>
        </div>
        <div className="min-w-0">
          <h3 className="font-serif text-[15px] text-[#221a12] truncate font-semibold">{unitName}</h3>
          <p className="text-[12px] font-semibold text-[#2e4856]">{troopCountText}</p>
        </div>
      </div>
      <div className="mt-2">
        <div className="flex justify-between text-[11px] text-[#42474b] mb-0.5">
          <span>Morale</span>
          <span className="font-semibold text-[#221a12]">{morale}%</span>
        </div>
        <div className="w-full bg-[#f5e5d8] h-1.5 rounded-full overflow-hidden">
          <div className="bg-[#5E8A5A] h-full rounded-full" style={{ width: `${morale}%` }} />
        </div>
      </div>
    </div>
  );
}
