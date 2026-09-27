import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown, Check, MessageSquare } from 'lucide-react';
import confetti from 'canvas-confetti';
import { api } from '../../services/api';

interface FeedbackButtonsProps {
  messageId?: string;
}

export const FeedbackButtons: React.FC<FeedbackButtonsProps> = ({ messageId }) => {
  const [rated, setRated] = useState<number | null>(null);
  const [showCommentInput, setShowCommentInput] = useState(false);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRate = async (rating: number) => {
    if (!messageId || rated !== null) return;
    setRated(rating);

    if (rating === 1) {
      // Trigger subtle celebration confetti
      try {
        confetti({
          particleCount: 30,
          spread: 45,
          origin: { y: 0.8 },
          colors: ['#00f2fe', '#4facfe', '#7928ca'],
        });
      } catch {}
    } else {
      setShowCommentInput(true);
    }

    try {
      await api.submitFeedback(messageId, rating);
    } catch {}
  };

  const handleCommentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!messageId || !comment.trim()) return;
    setIsSubmitting(true);
    try {
      await api.submitFeedback(messageId, rated || -1, comment);
      setShowCommentInput(false);
    } catch {} finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-2 mt-2">
      <div className="flex items-center gap-1.5 text-slate-400">
        <button
          onClick={() => handleRate(1)}
          disabled={rated !== null}
          className={`p-1.5 rounded-lg border transition-all ${
            rated === 1
              ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
              : 'border-transparent hover:border-white/10 hover:bg-white/5 hover:text-slate-200'
          }`}
          title="Accurate & helpful"
        >
          <ThumbsUp className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => handleRate(-1)}
          disabled={rated !== null}
          className={`p-1.5 rounded-lg border transition-all ${
            rated === -1
              ? 'bg-rose-500/20 border-rose-500/40 text-rose-400'
              : 'border-transparent hover:border-white/10 hover:bg-white/5 hover:text-slate-200'
          }`}
          title="Needs improvement"
        >
          <ThumbsDown className="w-3.5 h-3.5" />
        </button>
        {rated !== null && (
          <span className="text-[11px] text-cyan-400/80 font-mono ml-1 flex items-center gap-1">
            <Check className="w-3 h-3 text-cyan-400" /> Rated
          </span>
        )}
      </div>

      {showCommentInput && (
        <form onSubmit={handleCommentSubmit} className="flex gap-2 items-center bg-slate-900/80 p-2 rounded-xl border border-white/10">
          <input
            type="text"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Help improve: what went wrong?"
            className="flex-1 bg-transparent text-xs text-slate-200 focus:outline-none placeholder-slate-500 px-1"
          />
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-2.5 py-1 text-xs bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 rounded-lg border border-cyan-500/30 font-mono"
          >
            Submit
          </button>
        </form>
      )}
    </div>
  );
};
