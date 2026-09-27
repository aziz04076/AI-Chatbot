import React from 'react';
import { ShieldCheck, AlertCircle } from 'lucide-react';

interface ConfidenceBadgeProps {
  score?: number;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ score }) => {
  if (score === undefined || score === null) return null;

  const percentage = Math.round(score * 100);
  const isHigh = percentage >= 80;
  const isMedium = percentage >= 60 && percentage < 80;

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono border backdrop-blur-md transition-all ${
        isHigh
          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
          : isMedium
          ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
          : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
      }`}
      title={`AI Confidence Calibration: ${percentage}%`}
    >
      {isHigh ? <ShieldCheck className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
      <span>{percentage}% Confidence</span>
    </div>
  );
};
