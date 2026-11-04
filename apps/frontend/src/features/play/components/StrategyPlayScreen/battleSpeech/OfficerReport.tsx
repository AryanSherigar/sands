import type { OfficerReportProps } from "./OfficerReport.types";

export function OfficerReport({ report }: OfficerReportProps) {
  return (
    <blockquote className="rounded-md border-l-4 border-[#46606E] bg-[#EFE5C8] px-4 py-3 font-serif text-base italic">
      {report}
    </blockquote>
  );
}
