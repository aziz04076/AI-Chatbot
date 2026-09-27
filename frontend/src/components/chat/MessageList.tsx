import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Copy, Check, Terminal, BookOpen, Wrench, ChevronDown, ChevronUp, Bot, User as UserIcon, Zap } from 'lucide-react';
import { ChatMessage, AIState } from '../../types';
import { ConfidenceBadge } from './ConfidenceBadge';
import { FollowUpChips } from './FollowUpChips';
import { FeedbackButtons } from './FeedbackButtons';
import { MultiAgentReasoningPanel } from './MultiAgentReasoningPanel';
import { TraceWaterfall } from './TraceWaterfall';

interface MessageListProps {
  messages: ChatMessage[];
  aiState: AIState;
  onFollowUpClick: (prompt: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({ messages, aiState, onFollowUpClick }) => {
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);
  const [openTools, setOpenTools] = useState<Record<string, boolean>>({});

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(id);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const toggleTool = (id: string) => {
    setOpenTools((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const renderContent = (content: string, msgId: string) => {
    // Custom Markdown Parser for Code blocks and formatting
    const parts = content.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      if (part.startsWith('```')) {
        const firstLineEnd = part.indexOf('\n');
        const lang = part.slice(3, firstLineEnd).trim() || 'code';
        const code = part.slice(firstLineEnd + 1, -3);
        const codeBlockId = `${msgId}-code-${index}`;

        return (
          <div key={index} className="my-3 rounded-xl overflow-hidden border border-slate-700/60 bg-slate-950/80 shadow-2xl">
            <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900/90 border-b border-slate-800 text-xs font-mono text-slate-400">
              <span className="flex items-center gap-1.5 text-cyan-400">
                <Terminal className="w-3.5 h-3.5" />
                {lang}
              </span>
              <button
                onClick={() => copyToClipboard(code, codeBlockId)}
                className="flex items-center gap-1 px-2 py-0.5 rounded hover:bg-white/10 hover:text-white transition-colors"
                title="Copy code"
              >
                {copiedIndex === codeBlockId ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <pre className="p-3.5 text-xs font-mono text-cyan-100 overflow-x-auto selection:bg-cyan-700 selection:text-white leading-relaxed">
              <code>{code}</code>
            </pre>
          </div>
        );
      }

      // Format markdown bold, headers, and bullet points
      const lines = part.split('\n');
      return (
        <div key={index} className="space-y-1.5 text-sm sm:text-[15px] leading-relaxed">
          {lines.map((line, lIdx) => {
            if (line.startsWith('### ')) {
              return <h3 key={lIdx} className="text-base font-bold text-cyan-300 mt-2 mb-1">{line.slice(4)}</h3>;
            }
            if (line.startsWith('## ')) {
              return <h2 key={lIdx} className="text-lg font-bold text-white mt-3 mb-1.5">{line.slice(3)}</h2>;
            }
            if (line.startsWith('# ')) {
              return <h1 key={lIdx} className="text-xl font-bold text-white mt-4 mb-2">{line.slice(2)}</h1>;
            }
            if (line.startsWith('- ') || line.startsWith('* ')) {
              return (
                <div key={lIdx} className="flex items-start gap-2 pl-2">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span>{formatInlineMarkdown(line.slice(2))}</span>
                </div>
              );
            }
            if (!line.trim()) return <div key={lIdx} className="h-1" />;
            return <p key={lIdx}>{formatInlineMarkdown(line)}</p>;
          })}
        </div>
      );
    });
  };

  const formatInlineMarkdown = (text: string) => {
    // Bold **text**
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((p, i) => {
      if (p.startsWith('**') && p.endsWith('**')) {
        return <strong key={i} className="font-semibold text-white">{p.slice(2, -2)}</strong>;
      }
      if (p.startsWith('`') && p.endsWith('`')) {
        return <code key={i} className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono text-xs">{p.slice(1, -1)}</code>;
      }
      return p;
    });
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-6">
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center min-h-[50vh] text-center max-w-lg mx-auto p-8 rounded-3xl glass-panel border border-white/10 shadow-2xl">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-500/20 to-purple-500/20 border border-cyan-500/40 flex items-center justify-center mb-4 text-cyan-400 shadow-[0_0_25px_rgba(0,242,254,0.25)]">
            <Bot className="w-7 h-7" />
          </div>
          <h2 className="text-xl font-bold tracking-tight text-white mb-2">NexusAI Cloud Principal Intelligence</h2>
          <p className="text-sm text-slate-400 leading-relaxed mb-6">
            Fine-tuned Llama-3-8B architecture assistant. Equipped with live RAG vector search, agentic math/tools, and zero-downtime DevOps patterns.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full">
            {[
              "Calculate VRAM for Llama-3-8B in vLLM",
              "Production Kubernetes PDB & security spec",
              "Zero-Trust IAM & Secrets architecture",
              "ArgoCD multi-stage Helm deployment"
            ].map((prompt, i) => (
              <button
                key={i}
                onClick={() => onFollowUpClick(prompt)}
                className="p-3 text-left rounded-xl bg-slate-900/60 hover:bg-slate-800/80 border border-white/5 hover:border-cyan-500/30 text-xs text-slate-300 hover:text-cyan-300 transition-all shadow-sm"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {messages.map((msg) => {
        const isUser = msg.role === 'user';

        return (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ type: 'spring', stiffness: 350, damping: 25 }}
            className={`flex gap-3 sm:gap-4 max-w-4xl ${isUser ? 'ml-auto justify-end' : 'mr-auto justify-start'}`}
          >
            {!isUser && (
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-white shrink-0 shadow-lg mt-1">
                <Bot className="w-4 h-4" />
              </div>
            )}

            <div
              className={`flex-1 max-w-[85%] sm:max-w-[78%] rounded-2xl p-4 sm:p-5 transition-all shadow-xl ${
                isUser
                  ? 'bg-gradient-to-br from-cyan-600/90 to-blue-700/90 text-white rounded-tr-sm ml-auto border border-cyan-400/30'
                  : 'glass-panel rounded-tl-sm text-slate-200 border-white/10'
              }`}
            >
              {/* Multi-Agent Coordinated Reasoning Pipeline */}
              {msg.plan && <MultiAgentReasoningPanel plan={msg.plan} />}

              {/* Tool Execution Box */}
              {msg.tool_events && msg.tool_events.length > 0 && (
                <div className="mb-3 rounded-xl bg-slate-950/60 border border-cyan-500/20 overflow-hidden text-xs">
                  <button
                    onClick={() => toggleTool(msg.id)}
                    className="w-full flex items-center justify-between px-3 py-2 bg-cyan-950/30 text-cyan-300 font-mono hover:bg-cyan-900/30 transition-colors"
                  >
                    <span className="flex items-center gap-1.5">
                      <Wrench className="w-3.5 h-3.5 text-cyan-400" />
                      Agent Execution Step ({msg.tool_events.length} tools invoked)
                    </span>
                    {openTools[msg.id] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>
                  <AnimatePresence>
                    {openTools[msg.id] && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="p-3 space-y-2 border-t border-cyan-500/10 font-mono overflow-hidden"
                      >
                        {msg.tool_events.map((t, idx) => (
                          <div key={idx} className="space-y-1">
                            <div className="text-amber-400 font-medium">Tool: {t.tool}</div>
                            <div className="text-slate-400 pl-2">Input: {t.input}</div>
                            <div className="text-emerald-400 pl-2">Output: {t.output}</div>
                          </div>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}

              {/* Hybrid RAG Citations Box */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mb-3.5 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-cyan-400/80">
                    <Zap className="w-3 h-3 text-cyan-400" />
                    <span>Hybrid Retrieved Sources (BM25 + Dense Vector RRF):</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {msg.citations.map((c, cIdx) => (
                      <div
                        key={cIdx}
                        className="group relative inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 hover:border-indigo-400/50 text-[11px] font-mono text-indigo-300 transition-all cursor-help shadow-sm"
                        title={c.snippet}
                      >
                        <BookOpen className="w-3 h-3 text-indigo-400" />
                        <span className="font-semibold text-slate-200">{c.source}</span>
                        <span className="text-cyan-400 font-bold">({Math.round(c.similarity * 100)}%)</span>
                        {c.bm25_rank && c.vector_rank && (
                          <span className="text-[9px] px-1 py-0.2 rounded bg-indigo-950/60 text-indigo-300/80">
                            BM25 #{c.bm25_rank} · Vec #{c.vector_rank}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Message Content */}
              {renderContent(msg.content, msg.id)}

              {/* Distributed OpenTelemetry Waterfall */}
              {!isUser && msg.trace_id && (
                <TraceWaterfall
                  traceId={msg.trace_id}
                  traceparent={msg.traceparent}
                  spans={msg.trace_spans}
                />
              )}

              {/* Assistant Footer Metadata */}
              {!isUser && (
                <div className="mt-4 pt-3 border-t border-white/5 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <ConfidenceBadge score={msg.confidence_score} />
                    {msg.latency_ms && (
                      <span className="text-[11px] font-mono text-slate-500">
                        {msg.latency_ms}ms · {msg.tokens_generated || 0} tokens
                      </span>
                    )}
                  </div>
                  <FeedbackButtons messageId={msg.id} />
                </div>
              )}

              {/* Follow-up Chips */}
              {!isUser && (
                <FollowUpChips
                  suggestions={msg.follow_ups}
                  onSelect={onFollowUpClick}
                />
              )}
            </div>

            {isUser && (
              <div className="w-8 h-8 rounded-xl bg-slate-800 border border-white/10 flex items-center justify-center text-slate-300 shrink-0 shadow-lg mt-1">
                <UserIcon className="w-4 h-4" />
              </div>
            )}
          </motion.div>
        );
      })}

      {/* Shimmering 3D Loading Skeleton when AI is generating */}
      <AnimatePresence>
        {aiState === 'thinking' && (
          <motion.div
            initial={{ opacity: 0, y: 14, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 350, damping: 25 }}
            className="flex gap-3 sm:gap-4 max-w-4xl mr-auto w-full"
          >
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-white shrink-0 shadow-lg mt-1 animate-pulse">
              <Bot className="w-4 h-4" />
            </div>
            <div className="flex-1 max-w-[85%] sm:max-w-[78%] rounded-2xl p-4 sm:p-5 glass-panel rounded-tl-sm border border-cyan-500/30 space-y-4 relative overflow-hidden shadow-2xl animate-shimmer">
              {/* Plan Status Header Skeleton */}
              <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900/60 border border-cyan-500/20">
                <div className="w-3.5 h-3.5 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
                <span className="text-xs font-mono text-cyan-400 tracking-wide">Orchestrating multi-agent pipeline...</span>
              </div>

              {/* Reasoning Plan Skeleton Chips */}
              <div className="flex gap-2">
                <div className="h-5 w-24 rounded-md bg-slate-800/80 animate-pulse" />
                <div className="h-5 w-32 rounded-md bg-slate-800/80 animate-pulse" />
                <div className="h-5 w-20 rounded-md bg-slate-800/80 animate-pulse" />
              </div>

              {/* Layout-matched varied text bar skeletons */}
              <div className="space-y-2.5">
                <div className="h-4 bg-slate-800/90 rounded-md w-[88%]" />
                <div className="h-4 bg-slate-800/90 rounded-md w-[94%]" />
                <div className="h-4 bg-slate-800/90 rounded-md w-[68%]" />
              </div>

              {/* Live typing indicator with pulsating dots and trailing glow */}
              <div className="flex items-center gap-1.5 pt-1">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping opacity-75" />
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse delay-75 shadow-[0_0_8px_#00f2fe]" />
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse delay-150" />
                <span className="text-[11px] font-mono text-slate-500 ml-2">synthesizing tokens</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
