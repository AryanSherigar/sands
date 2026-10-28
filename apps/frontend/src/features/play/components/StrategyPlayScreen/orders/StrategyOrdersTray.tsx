import React from "react";
import { IconX } from "@tabler/icons-react";
import { describeOrder, type RegionNameLookup } from "../../../lib/orderSummary";
import type { QueuedOrderView } from "../../../types/simulation.types";
import type { StrategyOrdersTrayProps } from "./StrategyOrders.types";

function renderTrayHeader(count: number) {
  return (
    <div className="px-2.5 py-1 border-r border-[#3A3128]/15 pr-3 flex flex-col">
      <span className="text-[9px] text-[#46606E] uppercase font-bold tracking-wider">
        Turn Orders
      </span>
      <span className="text-xs font-bold text-[#221A12]">{count} Dispatched</span>
    </div>
  );
}

function renderOrderItem(
  order: QueuedOrderView,
  onCancelOrder: (commandId: string) => void,
  regionNames?: RegionNameLookup,
) {
  const handleCancel = () => onCancelOrder(order.id);

  return (
    <div
      key={order.id}
      className="px-2.5 py-1 rounded-lg bg-[#FBEBDE]/70 border border-[#3A3128]/10 flex items-center gap-2"
    >
      <div className="flex flex-col leading-tight">
        <span className="text-[10px] font-bold text-[#221A12]">{describeOrder(order.order, regionNames)}</span>
        <span className="text-[9px] text-[#72787C]">{order.cost} {order.cost === 1 ? "mandate" : "mandates"}</span>
      </div>
      {order.is_cancellable && (
        <button
          type="button"
          title="Cancel order"
          onClick={handleCancel}
          className="text-[#72787C] hover:text-[#A8483E] p-0.5 cursor-pointer flex items-center justify-center"
        >
          <IconX size={12} stroke={2} />
        </button>
      )}
    </div>
  );
}

function renderRemainingMandates(remaining: number, total: number) {
  return (
    <div className="px-2.5 py-1 rounded-lg border border-dashed border-[#72787C]/40 text-[#72787C] text-[10px] font-semibold">
      {remaining} / {total} Mandates Open
    </div>
  );
}

export const StrategyOrdersTray: React.FC<StrategyOrdersTrayProps> = ({
  orders,
  ordersRemaining = 0,
  ordersTotal = ordersRemaining,
  regionNames,
  onCancelOrder,
}) => {
  return (
    <div className="fixed bottom-4 left-4 z-40 flex items-center gap-2 pointer-events-auto">
      <div className="flex items-center gap-1.5 bg-[#F7F0DC]/95 backdrop-blur-xl p-1.5 rounded-xl border border-[#3A3128]/20 shadow-lg">
        {renderTrayHeader(orders.length)}
        {orders.map((order) => renderOrderItem(order, onCancelOrder, regionNames))}
        {renderRemainingMandates(ordersRemaining, ordersTotal)}
      </div>
    </div>
  );
};
