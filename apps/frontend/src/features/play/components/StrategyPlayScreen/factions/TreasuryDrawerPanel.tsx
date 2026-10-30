import React, { useState } from "react";
import {
  buildDeclareDefaultOrder,
  buildSetTaxRateOrder,
  buildTakeLoanOrder,
} from "../../../lib/orderBuilders";
import type { TaxRate } from "../../../types/simulation.types";
import type { TreasuryDrawerPanelProps } from "./TreasuryDrawerPanel.types";

const TAX_RATES: readonly TaxRate[] = ["low", "normal", "high"];

const TAX_MULTIPLIERS: Record<TaxRate, number> = {
  low: 0.5,
  normal: 0.8,
  high: 1.2,
};

const TAX_LABELS: Record<TaxRate, string> = {
  low: "Low",
  normal: "Normal",
  high: "High",
};

const PERCENT_BASE = 100;
const RADIX_DECIMAL = 10;

function estimateIncome(
  regions: TreasuryDrawerPanelProps["world"]["regions"],
  rate: TaxRate,
): number {
  return regions.reduce((sum, region) => {
    const detail = region.detail;
    if (!detail) return sum;
    const gross = (detail.wealth * TAX_MULTIPLIERS[rate] * (PERCENT_BASE - detail.unrest)) / PERCENT_BASE;
    return sum + Math.floor(gross);
  }, 0);
}

function hasAnyDetail(regions: TreasuryDrawerPanelProps["world"]["regions"]): boolean {
  return regions.some((region) => region.detail != null);
}

interface TaxRateButtonProps {
  rate: TaxRate;
  isActive: boolean;
  isPreviewed: boolean;
  onClick: () => void;
}

const TaxRateButton: React.FC<TaxRateButtonProps> = ({
  rate,
  isActive,
  isPreviewed,
  onClick,
}) => {
  const activeClass = isPreviewed
    ? "bg-[#46606E] text-white"
    : "bg-[#F5E5D8] border border-[#3A3128]/15 text-[#221A12] hover:bg-[#F0E0D2]";
  return (
    <button
      type="button"
      aria-pressed={isActive}
      onClick={onClick}
      className={`flex-1 py-1.5 rounded text-xs font-bold transition-colors ${activeClass}`}
    >
      {TAX_LABELS[rate]}
    </button>
  );
};

interface TaxRateButtonGroupProps {
  currentRate: TaxRate;
  previewRate: TaxRate;
  onRateClick: (rate: TaxRate) => void;
}

const TaxRateButtonGroup: React.FC<TaxRateButtonGroupProps> = ({
  currentRate,
  previewRate,
  onRateClick,
}) => (
  <div className="flex gap-1">
    {TAX_RATES.map((rate) => (
      <TaxRateButton
        key={rate}
        rate={rate}
        isActive={rate === currentRate}
        isPreviewed={rate === previewRate}
        onClick={() => onRateClick(rate)}
      />
    ))}
  </div>
);

interface TaxEstimateTextProps {
  income: number;
  rate: TaxRate;
  hasFoggedRegions: boolean;
}

const TaxEstimateText: React.FC<TaxEstimateTextProps> = ({
  income,
  rate,
  hasFoggedRegions,
}) => (
  <p className="text-[10px] text-[#72787C] leading-snug">
    ~{income.toLocaleString()}g income this turn at {TAX_LABELS[rate].toLowerCase()} tax
    {hasFoggedRegions ? " (excludes fogged regions)" : ""}
  </p>
);

interface TaxSectionProps {
  factionId: string;
  currentRate: TaxRate;
  regions: TreasuryDrawerPanelProps["world"]["regions"];
  onSubmitOrder: TreasuryDrawerPanelProps["onSubmitOrder"];
}

const TaxRateSection: React.FC<TaxSectionProps> = ({
  factionId,
  currentRate,
  regions,
  onSubmitOrder,
}) => {
  const [previewRate, setPreviewRate] = useState<TaxRate>(currentRate);
  const income = estimateIncome(regions, previewRate);
  const hasFogged = regions.some((region) => region.detail == null);

  const handleRateClick = (rate: TaxRate): void => {
    setPreviewRate(rate);
    if (rate !== currentRate) onSubmitOrder(buildSetTaxRateOrder(factionId, rate));
  };

  return (
    <div className="p-3 flex flex-col gap-2">
      <span className="text-[10px] text-[#46606E] font-bold uppercase tracking-widest">
        Tax Rate
      </span>
      <TaxRateButtonGroup
        currentRate={currentRate}
        previewRate={previewRate}
        onRateClick={handleRateClick}
      />
      {hasAnyDetail(regions) && (
        <TaxEstimateText income={income} rate={previewRate} hasFoggedRegions={hasFogged} />
      )}
    </div>
  );
};

interface LoanInputRowProps {
  amount: number;
  onAmountChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onSubmit: () => void;
}

const LoanInputRow: React.FC<LoanInputRowProps> = ({ amount, onAmountChange, onSubmit }) => (
  <div className="flex gap-1.5">
    <input
      type="number"
      min={1}
      value={amount || ""}
      onChange={onAmountChange}
      placeholder="Amount"
      className="flex-1 px-2 py-1 rounded border border-[#3A3128]/20 bg-[#FBEBDE]/60 text-xs font-mono text-[#221A12] placeholder-[#72787C]/60 focus:outline-none focus:border-[#46606E]/50"
    />
    <button
      type="button"
      disabled={amount <= 0}
      onClick={onSubmit}
      className="px-2 py-1 rounded bg-[#46606E] text-white text-xs font-bold disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90"
    >
      Contract Loan
    </button>
  </div>
);

interface LoanSummaryProps {
  loans: TreasuryDrawerPanelProps["world"]["my_faction"]["loans"];
}

const LoanSummary: React.FC<LoanSummaryProps> = ({ loans }) => {
  if (loans.length === 0) return null;
  const totalPrincipal = loans.reduce((sum, loan) => sum + loan.principal, 0);
  const loanSuffix = loans.length === 1 ? "loan" : "loans";
  return (
    <p className="text-[10px] text-[#72787C]">
      Outstanding principal: {totalPrincipal.toLocaleString()}g across {loans.length} {loanSuffix}
    </p>
  );
};

interface LoanSectionProps {
  factionId: string;
  loans: TreasuryDrawerPanelProps["world"]["my_faction"]["loans"];
  onSubmitOrder: TreasuryDrawerPanelProps["onSubmitOrder"];
}

const LoanSection: React.FC<LoanSectionProps> = ({ factionId, loans, onSubmitOrder }) => {
  const [amount, setAmount] = useState(0);

  const handleAmountChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    setAmount(Math.max(0, parseInt(event.target.value, RADIX_DECIMAL) || 0));
  };

  const handleContractLoan = (): void => {
    if (amount <= 0) return;
    onSubmitOrder(buildTakeLoanOrder(factionId, amount));
    setAmount(0);
  };

  return (
    <div className="p-3 flex flex-col gap-2 border-t border-[#72787C]/20">
      <span className="text-[10px] text-[#46606E] font-bold uppercase tracking-widest">
        Sovereign Credit
      </span>
      <LoanSummary loans={loans} />
      <LoanInputRow
        amount={amount}
        onAmountChange={handleAmountChange}
        onSubmit={handleContractLoan}
      />
    </div>
  );
};

interface DefaultSectionProps {
  factionId: string;
  onSubmitOrder: TreasuryDrawerPanelProps["onSubmitOrder"];
}

const DefaultSection: React.FC<DefaultSectionProps> = ({ factionId, onSubmitOrder }) => {
  const handleDeclareDefault = (): void => {
    onSubmitOrder(buildDeclareDefaultOrder(factionId));
  };

  return (
    <div className="p-3 flex flex-col gap-2 border-t border-[#72787C]/20">
      <span className="text-[10px] text-[#46606E] font-bold uppercase tracking-widest">
        Sovereign Default
      </span>
      <button
        type="button"
        onClick={handleDeclareDefault}
        className="w-full py-1.5 rounded border border-[#A8483E]/40 bg-[#FFF0EE] text-[#A8483E] text-xs font-bold hover:bg-[#FFE4E0] transition-colors"
      >
        Declare Default
      </button>
      <p className="text-[10px] text-[#72787C] leading-snug">
        Armies go unpaid. Stability and reputation fall.
      </p>
    </div>
  );
};

export const TreasuryDrawerPanel: React.FC<TreasuryDrawerPanelProps> = ({
  world,
  onSubmitOrder,
}) => {
  const { my_faction, regions } = world;

  return (
    <div className="flex flex-col">
      <TaxRateSection
        factionId={my_faction.id}
        currentRate={my_faction.tax_rate}
        regions={regions}
        onSubmitOrder={onSubmitOrder}
      />
      <LoanSection
        factionId={my_faction.id}
        loans={my_faction.loans}
        onSubmitOrder={onSubmitOrder}
      />
      <DefaultSection factionId={my_faction.id} onSubmitOrder={onSubmitOrder} />
    </div>
  );
};
