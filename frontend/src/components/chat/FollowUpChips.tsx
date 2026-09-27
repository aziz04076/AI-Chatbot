import React from 'react';
import { Sparkles, ArrowRight } from 'lucide-react';

interface FollowUpChipsProps {
  suggestions?: string[];
  onSelect: (prompt: string) => void;
}

export const FollowUpChips: React.FC<FollowUpChipsProps> = ({ suggestions, onSelect }) => {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-2 pt-2 border-t border-white/5">
      <div className="w-full flex items-center gap-1.5 text-xs text-cyan-400/80 font-mono mb-1">
        <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
        <span>Suggested Architecture Inquiries:</span>
      </div>
      {suggestions.map((prompt, idx) => (
        <button
          key={idx}
          onClick={() => onSelect(prompt)}
          className="group flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-xl bg-slate-800/60 hover:bg-cyan-950/60 border border-slate-700/60 hover:border-cyan-500/40 text-slate-300 hover:text-cyan-200 transition-all text-left shadow-sm"
        >
          <span>{prompt}</span>
          <ArrowRight className="w-3 h-3 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all text-cyan-400" />
        </button>
      ))}
    </div>
  );
};
