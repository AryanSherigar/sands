import React from "react";
import type { LetterManuscriptSheetProps } from "./LetterPouchStage.types";
import { LetterBrokenSeal } from "./LetterBrokenSeal";

function ManuscriptHeader({
  locationHeader,
  isSealIntact,
}: {
  locationHeader: string;
  isSealIntact: boolean;
}) {
  const sealBadgeText = isSealIntact ? "Seal intact prior to dawn" : "Inspected by bailiff";
  return (
    <div className="flex justify-between items-baseline mb-6 pb-2 border-b border-on-surface/10 relative z-10">
      <span className="font-display italic text-body-sm text-on-surface-variant/80">{locationHeader}</span>
      <span className="font-label-md text-[10px] uppercase tracking-widest text-on-surface-variant/70 font-semibold bg-[#ede1c7] px-2 py-0.5 rounded">
        {sealBadgeText}
      </span>
    </div>
  );
}

function ManuscriptSalutation({
  portraitUrl,
  salutation,
}: {
  portraitUrl: string;
  salutation: string;
}) {
  return (
    <div className="flex items-start gap-3.5 mb-5 relative z-10">
      <div className="relative flex-shrink-0">
        <div className="absolute -top-7 left-1/2 -translate-x-1/2 w-3.5 h-8 bg-gradient-to-b from-[#8f271e] to-tertiary shadow-xs rounded-t-xs" />
        <div className="relative z-10 w-14 h-14 rounded-md p-1 bg-gradient-to-tr from-[#947432] via-[#e8cb7a] to-[#7a591e] shadow-md">
          <div className="w-full h-full rounded-xs overflow-hidden bg-parchment-base">
            {portraitUrl ? (
              <img src={portraitUrl} alt="Miniature" className="w-full h-full object-cover object-top" />
            ) : null}
          </div>
        </div>
      </div>
      <div className="pt-1">
        <span className="font-label-md text-[10px] uppercase tracking-wider text-secondary font-bold">
          Royal Missive
        </span>
        <h1 className="font-display text-[22px] sm:text-headline-sm text-on-surface font-semibold tracking-wide leading-tight">
          {salutation}
        </h1>
      </div>
    </div>
  );
}

function ManuscriptSignoff({
  signoffPlace,
  signoffSignature,
}: {
  signoffPlace: string;
  signoffSignature: string;
}) {
  return (
    <div className="mt-6 pt-2 flex flex-col items-end relative z-10">
      <p className="font-display italic text-body-sm text-on-surface-variant text-right">{signoffPlace}</p>
      <div className="mt-2 text-right">
        <span className="font-display text-[25px] font-semibold text-on-surface tracking-wide block">
          {signoffSignature}
        </span>
        <svg
          className="w-36 h-5 text-on-surface/75 mt-0.5 inline-block"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 160 28"
        >
          <path
            d="M4 14C30 4 55 24 85 13C110 3 130 22 156 12M28 20C65 14 105 26 142 16"
            strokeLinecap="round"
            strokeWidth="1.4"
          />
        </svg>
      </div>
    </div>
  );
}

function ManuscriptFooter() {
  return (
    <div className="mt-5 pt-4 border-t border-on-surface/10 flex items-center justify-between relative z-10">
      <LetterBrokenSeal />
      <div className="px-2.5 py-1 rounded bg-[#ece0c4] text-on-surface-variant text-[10px] font-label-md uppercase tracking-wider border border-[#dacbb1]">
        Folded once by hand
      </div>
    </div>
  );
}

export const LetterManuscriptSheet: React.FC<LetterManuscriptSheetProps> = ({
  incoming,
  portraitUrl,
}) => (
  <section aria-label="Letter Manuscript" className="lg:col-span-6 flex justify-center order-1 lg:order-2">
    <article className="relative w-full bg-[#f6efe1] bg-[radial-gradient(circle_at_75%_25%,#fcf8ee_0%,#f4eada_60%,#eae0c7_100%)] rounded-sm p-6 sm:p-9 md:p-12 shadow-xl border border-[#ded0b1]">
      <ManuscriptHeader locationHeader={incoming.locationHeader} isSealIntact={incoming.isSealIntactPriorToDawn} />
      <ManuscriptSalutation portraitUrl={portraitUrl} salutation={incoming.salutation} />
      <div className="flex flex-col gap-4 font-display text-[17px] sm:text-[18px] leading-[28px] sm:leading-[30px] text-on-surface font-normal relative z-10">
        {incoming.paragraphs.map((para, i) => (
          <p key={i}>{para}</p>
        ))}
      </div>
      <ManuscriptSignoff signoffPlace={incoming.signoffPlace} signoffSignature={incoming.signoffSignature} />
      <ManuscriptFooter />
    </article>
  </section>
);
