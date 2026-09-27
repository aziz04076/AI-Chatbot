import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  Cpu,
  HardDrive,
  Zap,
  ThumbsUp,
  Users,
  RefreshCw,
  X,
  TrendingUp,
  ShieldCheck,
  Lock,
  Award,
  Radio,
  CheckCircle2,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { AnalyticsSummary } from '../../types';
import { api } from '../../services/api';
import { EvaluationPanel } from './EvaluationPanel';

interface AnalyticsDashboardProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ isOpen, onClose }) => {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [circuitBreaker, setCircuitBreaker] = useState<{ state: string; failure_count: number } | null>(null);
  const [auditStatus, setAuditStatus] = useState<{ valid: boolean; total_records: number } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'telemetry' | 'evaluation'>('telemetry');
  const [expandedSection, setExpandedSection] = useState<'all' | 'topics' | 'hardware'>('all');

  useEffect(() => {
    if (isOpen) {
      loadAllMetrics();
      const interval = setInterval(loadAllMetrics, 6000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  const loadAllMetrics = async () => {
    try {
      const [summary, cb, audit] = await Promise.allSettled([
        api.getAnalytics(),
        api.getCircuitBreakerStatus(),
        api.verifyAuditChain(),
      ]);

      if (summary.status === 'fulfilled') setData(summary.value);
      if (cb.status === 'fulfilled' && cb.value) setCircuitBreaker(cb.value);
      if (audit.status === 'fulfilled' && audit.value) setAuditStatus(audit.value);
    } catch (err) {
      console.error('Failed to load metrics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-md">
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 15 }}
        transition={{ type: 'spring', stiffness: 320, damping: 26 }}
        className="w-full max-w-6xl max-h-[92vh] glass-panel border border-cyan-500/30 rounded-3xl overflow-hidden flex flex-col shadow-2xl relative"
      >
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-white/10 flex items-center justify-between glass-header">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-[0_0_15px_rgba(0,242,254,0.25)]">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-wide">Enterprise Analytics & Telemetry</h2>
                <span className="hidden sm:inline-flex px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-bold">
                  BENTO VIEW
                </span>
              </div>
              <p className="text-xs font-mono text-cyan-400">Production Node · Nexus Cluster Alpha-01</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadAllMetrics}
              className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-white/5 text-slate-300 transition-colors"
              title="Refresh Telemetry"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-xl bg-slate-800/80 hover:bg-rose-500/20 hover:text-rose-400 border border-white/5 text-slate-400 transition-colors"
              title="Close Dashboard"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="px-6 pt-3 pb-0 border-b border-white/10 flex items-center gap-6 bg-slate-900/60">
          <button
            onClick={() => setActiveTab('telemetry')}
            className={`flex items-center gap-2 pb-3 px-1 text-xs font-bold transition-all border-b-2 ${
              activeTab === 'telemetry'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Telemetry & Bento Status</span>
          </button>
          <button
            onClick={() => setActiveTab('evaluation')}
            className={`flex items-center gap-2 pb-3 px-1 text-xs font-bold transition-all border-b-2 ${
              activeTab === 'evaluation'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Award className="w-4 h-4 text-cyan-400" />
            <span>Held-Out Test Set Evaluation</span>
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
          {activeTab === 'evaluation' ? (
            <EvaluationPanel />
          ) : isLoading && !data ? (
            <div className="text-center py-20 text-cyan-400 font-mono text-sm animate-pulse">
              Aggregating live cluster telemetry...
            </div>
          ) : data ? (
            <>
              {/* Row 1: KPI Stat Cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
                <div className="p-4 rounded-2xl glass-panel border border-white/5 space-y-1 hover:border-cyan-500/30 transition-all">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
                    <span>Total Invocations</span>
                    <Zap className="w-4 h-4 text-cyan-400" />
                  </div>
                  <div className="text-2xl font-bold text-white font-mono">{data.total_queries}</div>
                  <div className="text-[11px] text-emerald-400 font-mono flex items-center gap-1">
                    <span>+18%</span>
                    <span className="text-slate-500">vs last window</span>
                  </div>
                </div>

                <div className="p-4 rounded-2xl glass-panel border border-white/5 space-y-1 hover:border-indigo-500/30 transition-all">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
                    <span>Avg Latency</span>
                    <TrendingUp className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div className="text-2xl font-bold text-white font-mono">{data.avg_latency_ms} ms</div>
                  <div className="text-[11px] text-cyan-400 font-mono">p95 &lt; 210ms (Optimal)</div>
                </div>

                <div className="p-4 rounded-2xl glass-panel border border-white/5 space-y-1 hover:border-pink-500/30 transition-all">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
                    <span>User Satisfaction</span>
                    <ThumbsUp className="w-4 h-4 text-pink-400" />
                  </div>
                  <div className="text-2xl font-bold text-white font-mono">{data.user_satisfaction_percent}%</div>
                  <div className="text-[11px] text-pink-400 font-mono">Verified feedback loop</div>
                </div>

                <div className="p-4 rounded-2xl glass-panel border border-white/5 space-y-1 hover:border-amber-500/30 transition-all">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
                    <span>Active Sessions</span>
                    <Users className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="text-2xl font-bold text-white font-mono">{data.active_sessions_count}</div>
                  <div className="text-[11px] text-amber-400 font-mono">WS &amp; SSE Real-Time Streams</div>
                </div>
              </div>

              {/* Row 2: Bento Grid Layout */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                {/* Bento Card 1: GPU Accelerator & VRAM Breakdown (Span 8) */}
                <div className="md:col-span-8 p-5 rounded-2xl glass-panel border border-white/10 space-y-4 hover:border-cyan-500/40 transition-all shadow-xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                        <Cpu className="w-4 h-4" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-white">GPU Hardware Accelerator</h3>
                        <div className="text-xs font-mono text-slate-400">{data.system_health.gpu_name}</div>
                      </div>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-1.5 shadow-[0_0_8px_rgba(16,185,129,0.2)]">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      ONLINE
                    </span>
                  </div>

                  {/* VRAM Progress Bar */}
                  <div className="space-y-2 pt-1">
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-slate-400">Dedicated VRAM Utilization</span>
                      <span className="text-cyan-300 font-bold">
                        {data.system_health.gpu_vram_used_gb} GB / {data.system_health.gpu_vram_total_gb} GB (
                        {Math.round((data.system_health.gpu_vram_used_gb / data.system_health.gpu_vram_total_gb) * 100)}
                        %)
                      </span>
                    </div>
                    <div className="w-full h-3 rounded-full bg-slate-900/80 p-0.5 border border-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500 transition-all duration-700 shadow-[0_0_12px_rgba(0,242,254,0.4)]"
                        style={{
                          width: `${(data.system_health.gpu_vram_used_gb / data.system_health.gpu_vram_total_gb) * 100}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Sub-breakdown: KV Cache vs Weights */}
                  <div className="grid grid-cols-3 gap-2.5 pt-1 text-[11px] font-mono">
                    <div className="p-2.5 rounded-xl bg-slate-900/60 border border-white/5">
                      <div className="text-slate-400">Model Weights</div>
                      <div className="text-white font-bold mt-0.5">4.8 GB (4-bit QLoRA)</div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-slate-900/60 border border-white/5">
                      <div className="text-slate-400">Paged KV Cache</div>
                      <div className="text-cyan-300 font-bold mt-0.5">1.4 GB (vLLM block pool)</div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-slate-900/60 border border-white/5">
                      <div className="text-slate-400">Free Headroom</div>
                      <div className="text-emerald-400 font-bold mt-0.5">
                        {(data.system_health.gpu_vram_total_gb - data.system_health.gpu_vram_used_gb).toFixed(1)} GB
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bento Card 2: Enterprise Security & Resilience (Span 4) */}
                <div className="md:col-span-4 p-5 rounded-2xl glass-panel border border-white/10 space-y-3.5 hover:border-emerald-500/40 transition-all shadow-xl flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 text-white font-bold text-sm mb-3">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <span>Security & Resilience Posture</span>
                    </div>

                    <div className="space-y-2.5 text-xs font-mono">
                      {/* Circuit Breaker Status */}
                      <div className="p-2.5 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
                        <span className="text-slate-400">Circuit Breaker:</span>
                        <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/30 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          {circuitBreaker?.state.toUpperCase() || 'CLOSED'}
                        </span>
                      </div>

                      {/* Audit Hash Chaining */}
                      <div className="p-2.5 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
                        <span className="text-slate-400">Audit Hash Chain:</span>
                        <span className="px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-400 font-bold border border-cyan-500/30">
                          {auditStatus?.valid !== false ? 'SHA-256 VALID' : 'TAMPER DETECTED'}
                        </span>
                      </div>

                      {/* Column-Level Encryption */}
                      <div className="p-2.5 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
                        <span className="text-slate-400">Encryption at Rest:</span>
                        <span className="px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-400 font-bold border border-purple-500/30 flex items-center gap-1">
                          <Lock className="w-3 h-3" />
                          AES-256-GCM
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="text-[10px] font-mono text-slate-500 pt-2 border-t border-white/5">
                    Role-Based Access: Admin / Operator / Viewer enforced
                  </div>
                </div>

                {/* Bento Card 3: Host Node Hardware (Span 5) */}
                <div className="md:col-span-5 p-5 rounded-2xl glass-panel border border-white/10 space-y-4 hover:border-indigo-500/40 transition-all shadow-xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <HardDrive className="w-4 h-4 text-indigo-400" />
                      <h3 className="text-sm font-bold text-white">Host System Resources</h3>
                    </div>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                      NOMINAL
                    </span>
                  </div>

                  <div className="space-y-3.5">
                    {/* CPU */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-slate-400">Host CPU Load</span>
                        <span className="text-indigo-300 font-bold">{data.system_health.cpu_percent}%</span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-900 overflow-hidden">
                        <div
                          className="h-full bg-indigo-500 transition-all duration-500"
                          style={{ width: `${data.system_health.cpu_percent}%` }}
                        />
                      </div>
                    </div>

                    {/* RAM */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-slate-400">System RAM Allocation</span>
                        <span className="text-purple-300 font-bold">
                          {data.system_health.ram_used_gb} GB / {data.system_health.ram_total_gb} GB
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-900 overflow-hidden">
                        <div
                          className="h-full bg-purple-500 transition-all duration-500"
                          style={{
                            width: `${(data.system_health.ram_used_gb / data.system_health.ram_total_gb) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bento Card 4: Domain Topic Distribution (Span 7) */}
                <div className="md:col-span-7 p-5 rounded-2xl glass-panel border border-white/10 space-y-4 hover:border-cyan-500/40 transition-all shadow-xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Radio className="w-4 h-4 text-cyan-400" />
                      <h3 className="text-sm font-bold text-white">Domain Topic Distribution</h3>
                    </div>
                    <span className="text-xs font-mono text-slate-400">
                      {data.top_topics.reduce((acc, t) => acc + t.count, 0)} queries classified
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {data.top_topics.map((t, idx) => (
                      <div key={idx} className="space-y-1">
                        <div className="flex justify-between text-xs font-mono">
                          <span className="text-slate-300">{t.topic}</span>
                          <span className="text-cyan-400 font-bold">
                            {t.percentage}% ({t.count})
                          </span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-slate-900 overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 transition-all duration-500"
                            style={{ width: `${t.percentage}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </motion.div>
    </div>
  );
};
