import { describeEnemyEstimate, describeLossesByType, sumOwnLosses } from "../../../lib/battleReports";
import type { ExchangeReport } from "../StrategyWarCouncil.types";

export interface EngagementPrediction {
  title: string;
  friendlyLosses: string;
  enemyLosses: string;
  note: string;
}

export interface EngagementChronicleProps {
  reports: ExchangeReport[];
  activeDoctrineName: string;
  prediction: EngagementPrediction | null;
}

export function EngagementChronicle({ reports, activeDoctrineName, prediction }: EngagementChronicleProps) {
  return (
    <div className="p-3 rounded-xl bg-[#fff8f4]/90 shadow-sm border border-[#3A3128]/10 flex flex-col gap-2">
      <div className="flex items-center justify-between border-b pb-1 border-[#3A3128]/10">
        <div className="flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[#785a00] text-[18px]">history_edu</span>
          <h2 className="font-serif text-[17px] text-[#221a12]">Engagement Chronicle</h2>
        </div>
        <span className="text-[10px] uppercase font-bold text-[#72787c]">{activeDoctrineName}</span>
      </div>

      <div className="flex flex-col gap-2">
        {reports.length === 0 ? (
          <p className="text-[12px] text-[#42474b] italic p-2 bg-[#fff8f4]/80 rounded border border-[#3A3128]/5">
            No exchange has been fought yet.
          </p>
        ) : (
          reports.map((report, index) => (
            <div key={report.total_exchange} className="p-2 rounded bg-[#fff8f4]/80 border border-[#3A3128]/5">
              <div className="flex justify-between items-center mb-0.5">
                <span className="text-[10px] uppercase font-bold text-[#2e4856]">
                  Round {report.exchange_index} • Wave Exchange
                </span>
                <span className="text-[11px] text-[#5E8A5A] font-semibold">
                  Losses: {sumOwnLosses([report])}
                </span>
              </div>
              <p className="text-[12px] text-[#221a12] leading-tight">
                {report.outcome ?? "The exchange was fought."}
              </p>
              <p className="mt-0.5 text-[11px] text-[#42474b]">
                Our fallen: {describeLossesByType(report.own_losses)}. {describeEnemyEstimate(report, reports[index - 1])}.
              </p>
            </div>
          ))
        )}

        {prediction && <PredictionCard prediction={prediction} />}
      </div>
    </div>
  );
}

function PredictionCard({ prediction }: { prediction: EngagementPrediction }) {
  return (
    <div className="p-2.5 rounded-lg bg-[#f5e5d8]/90 shadow-xs border border-[#3A3128]/10 mt-0.5">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="material-symbols-outlined text-[#785a00] text-[18px]">verified</span>
        <p className="font-serif text-[14px] text-[#221a12] font-semibold">{prediction.title}</p>
      </div>
      <div className="grid grid-cols-2 gap-2 text-[11px] mt-1">
        <div>
          <span className="text-[#42474b] block">Expected friendly losses:</span>
          <span className="font-bold text-[#221a12]">{prediction.friendlyLosses}</span>
        </div>
        <div>
          <span className="text-[#42474b] block">Expected enemy losses:</span>
          <span className="font-bold text-[#7c2820]">{prediction.enemyLosses}</span>
        </div>
      </div>
      <p className="text-[11px] text-[#42474b] italic mt-1 pt-1 border-t border-[#3A3128]/10">{prediction.note}</p>
    </div>
  );
}
