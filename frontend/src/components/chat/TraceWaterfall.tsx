import React, { useState } from 'react';
import { Activity, Clock, Copy, Check, ChevronDown, ChevronUp, Layers, Cpu, Database, Bot } from 'lucide-react';
import { TraceSpan } from '../../types';

interface TraceWaterfallProps {
  traceId?: string;
  traceparent?: string;
  spans?: TraceSpan[];
}

export const TraceWaterfall: React.FC<TraceWaterfallProps> = ({ traceId, traceparent, spans }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [expandedSpan, setExpandedSpan] = useState<string | null>(null);

  if (!traceId || !spans || spans.length === 0) {
    return null;
  }

  // Find max duration to normalize horizontal waterfall bars
  const maxDuration = Math.max(...spans.map((s) => s.duration_ms || 1), 1);
  const totalDuration = spans.find((s) => !s.parent_span_id)?.duration_ms ||
    spans.reduce((acc, curr) => acc + (curr.parent_span_id ? 0 : curr.duration_ms), 0) ||
    maxDuration;

  const copyTrace = () => {
    navigator.clipboard.writeText(traceparent || traceId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getSpanIcon = (name: string) => {
    if (name.includes('rag') || name.includes('retrieval')) return <Database className="w-3.5 h-3.5 text-cyan-400" />;
    if (name.includes('agent') || name.includes('plan')) return <Bot className="w-3.5 h-3.5 text-purple-400" />;
    if (name.includes('llm') || name.includes('inference')) return <Cpu className="w-3.5 h-3.5 text-amber-400" />;
    return <Layers className="w-3.5 h-3.5 text-indigo-400" />;
  };

  const getSpanColor = (name: string) => {
    if (name.includes('rag') || name.includes('retrieval')) return 'from-cyan-500 to-teal-400';
    if (name.includes('agent') || name.includes('plan')) return 'from-purple-500 to-pink-500';
    if (name.includes('llm') || name.includes('inference')) return 'from-amber-500 to-emerald-400';
    return 'from-indigo-500 to-blue-500';
  };

  return (
    <div className="mt-2.5 rounded-xl border border-indigo-500/20 bg-slate-950/60 overflow-hidden text-xs">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-2 bg-indigo-950/20 hover:bg-indigo-950/40 text-indigo-300 font-mono transition-colors"
      >
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
          <span className="font-semibold text-slate-200">OpenTelemetry Trace</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            {spans.length} spans · {totalDuration.toFixed(1)}ms
          </span>
          <span className="text-[10px] text-slate-500 font-mono hidden sm:inline">
            ID: {traceId.slice(0, 8)}...{traceId.slice(-6)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-3.5 space-y-3 border-t border-indigo-500/10 font-mono bg-slate-950/80">
          {/* Header Metadata */}
          <div className="flex flex-wrap items-center justify-between gap-2 p-2 rounded-lg bg-slate-900/60 border border-white/5 text-[11px]">
            <div className="flex items-center gap-2 text-slate-400">
              <span className="text-slate-500">Traceparent:</span>
              <span className="text-cyan-300 select-all break-all">{traceparent || `00-${traceId}-01`}</span>
            </div>
            <button
              onClick={copyTrace}
              className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Copied' : 'Copy W3C Header'}</span>
            </button>
          </div>

          {/* Distributed Trace Spans Waterfall Chart */}
          <div className="space-y-2 pt-1">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold flex items-center justify-between">
              <span>Pipeline Operation Waterfall</span>
              <span>Duration</span>
            </div>

            {spans.map((span) => {
              const widthPct = Math.max(Math.min((span.duration_ms / maxDuration) * 100, 100), 5);
              const isChild = !!span.parent_span_id;
              const isExpanded = expandedSpan === span.span_id;

              return (
                <div key={span.span_id} className="space-y-1">
                  <div
                    onClick={() => setExpandedSpan(isExpanded ? null : span.span_id)}
                    className={`flex items-center justify-between p-1.5 rounded-md hover:bg-slate-900/80 cursor-pointer transition-colors ${
                      isChild ? 'pl-4 border-l-2 border-indigo-500/30' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      {getSpanIcon(span.name)}
                      <span className="font-medium text-slate-200 truncate">{span.name}</span>
                      <span
                        className={`text-[9px] px-1 rounded font-bold ${
                          span.status === 'OK'
                            ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-500/30'
                            : 'bg-rose-950/60 text-rose-400 border border-rose-500/30'
                        }`}
                      >
                        {span.status}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {/* Waterfall Progress Bar */}
                      <div className="w-24 sm:w-36 h-2 bg-slate-800 rounded-full overflow-hidden flex items-center">
                        <div
                          className={`h-full rounded-full bg-gradient-to-r ${getSpanColor(span.name)} shadow-[0_0_8px_rgba(99,102,241,0.5)]`}
                          style={{ width: `${widthPct}%` }}
                        />
                      </div>
                      <span className="text-[11px] text-slate-300 font-mono w-16 text-right">
                        {span.duration_ms.toFixed(1)}ms
                      </span>
                    </div>
                  </div>

                  {/* Expanded Span Attributes Detail */}
                  {isExpanded && span.attributes && Object.keys(span.attributes).length > 0 && (
                    <div className="ml-6 p-2 rounded bg-slate-900/90 border border-white/5 text-[10px] space-y-1">
                      <div className="text-slate-500 font-semibold">Span Attributes:</div>
                      {Object.entries(span.attributes).map(([k, v]) => (
                        <div key={k} className="flex gap-2">
                          <span className="text-cyan-400">{k}:</span>
                          <span className="text-slate-300 break-all">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
