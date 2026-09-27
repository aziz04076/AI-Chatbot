import React, { useState } from 'react';
import { 
  Network, 
  Cpu, 
  Search, 
  Code2, 
  CheckCircle2, 
  Clock, 
  Loader2, 
  AlertCircle, 
  ChevronDown, 
  ChevronUp, 
  Sparkles,
  ArrowRight
} from 'lucide-react';
import { TaskPlan, SubTask } from '../../types';

interface MultiAgentReasoningPanelProps {
  plan: TaskPlan;
}

export const MultiAgentReasoningPanel: React.FC<MultiAgentReasoningPanelProps> = ({ plan }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [expandedTasks, setExpandedTasks] = useState<Record<string, boolean>>({});

  const toggleTask = (taskId: string) => {
    setExpandedTasks((prev) => ({ ...prev, [taskId]: !prev[taskId] }));
  };

  const completedCount = plan.tasks.filter((t) => t.status === 'completed').length;
  const isAllComplete = completedCount === plan.tasks.length && plan.tasks.length > 0;

  const getAgentMeta = (role: string) => {
    switch (role) {
      case 'infra_calculation':
        return {
          label: 'Infra Calculation Agent',
          icon: Cpu,
          badgeColor: 'bg-amber-500/10 border-amber-500/30 text-amber-300',
          dotColor: 'bg-amber-400',
        };
      case 'code_architect':
        return {
          label: 'Code Architect Agent',
          icon: Code2,
          badgeColor: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
          dotColor: 'bg-emerald-400',
        };
      case 'research':
      default:
        return {
          label: 'Research Specialist Agent',
          icon: Search,
          badgeColor: 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300',
          dotColor: 'bg-indigo-400',
        };
    }
  };

  return (
    <div className="mb-4 rounded-2xl bg-slate-950/70 border border-cyan-500/30 overflow-hidden shadow-2xl transition-all">
      {/* Pipeline Header */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-cyan-950/40 via-indigo-950/30 to-slate-900/40 border-b border-cyan-500/20 cursor-pointer hover:bg-cyan-950/50 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-[0_0_10px_rgba(0,242,254,0.3)]">
            <Network className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-white tracking-wide flex items-center gap-2">
              <span>Multi-Agent Reasoning Pipeline</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-cyan-300">
                {plan.tasks.length} Subtasks Coordinated
              </span>
            </div>
            <div className="text-[11px] font-mono text-slate-400">
              {isAllComplete ? (
                <span className="text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" /> All specialized agents executed successfully
                </span>
              ) : (
                <span>
                  Progress: {completedCount} / {plan.tasks.length} subtasks completed
                </span>
              )}
            </div>
          </div>
        </div>

        <button className="p-1 rounded-lg text-slate-400 hover:text-white transition-colors">
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Pipeline Body */}
      {isExpanded && (
        <div className="p-3 sm:p-4 space-y-2.5 bg-slate-950/40">
          {plan.tasks.map((task, index) => {
            const agentMeta = getAgentMeta(task.assigned_agent);
            const AgentIcon = agentMeta.icon;
            const isTaskOpen = expandedTasks[task.id] ?? false;

            return (
              <div
                key={task.id}
                className="rounded-xl border border-white/5 bg-slate-900/50 overflow-hidden transition-all hover:border-white/10"
              >
                {/* Step Row */}
                <div
                  onClick={() => toggleTask(task.id)}
                  className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/5 transition-colors gap-2"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {/* Status Icon */}
                    <div className="shrink-0">
                      {task.status === 'completed' ? (
                        <div className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/40">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        </div>
                      ) : task.status === 'running' ? (
                        <div className="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center border border-amber-500/40 animate-pulse">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        </div>
                      ) : task.status === 'failed' ? (
                        <div className="w-5 h-5 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center border border-rose-500/40">
                          <AlertCircle className="w-3.5 h-3.5" />
                        </div>
                      ) : (
                        <div className="w-5 h-5 rounded-full bg-slate-800 text-slate-500 flex items-center justify-center border border-white/5">
                          <Clock className="w-3 h-3" />
                        </div>
                      )}
                    </div>

                    {/* Step Title & Agent Badge */}
                    <div className="truncate">
                      <div className="text-xs font-semibold text-slate-200 truncate flex items-center gap-2">
                        <span>{task.title}</span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono border ${agentMeta.badgeColor}`}
                        >
                          <AgentIcon className="w-3 h-3" />
                          <span>{agentMeta.label}</span>
                        </span>
                        {task.dependencies && task.dependencies.length > 0 && (
                          <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
                            <ArrowRight className="w-2.5 h-2.5" /> waits on {task.dependencies.join(', ')}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Open details chevron */}
                  {(task.thought || task.output) && (
                    <button className="text-slate-500 hover:text-slate-300 p-1">
                      {isTaskOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                  )}
                </div>

                {/* Expanded Details Drawer */}
                {isTaskOpen && (task.thought || task.output) && (
                  <div className="px-3.5 pb-3 pt-1 border-t border-white/5 bg-slate-950/60 space-y-2 font-mono text-xs">
                    {task.thought && (
                      <div className="space-y-1">
                        <div className="text-[11px] text-amber-400/90 flex items-center gap-1 font-semibold">
                          <Sparkles className="w-3 h-3 text-amber-400" />
                          <span>Internal Agent Thought & Reasoning:</span>
                        </div>
                        <p className="text-slate-400 pl-2 border-l border-amber-500/30 leading-relaxed text-[11px]">
                          {task.thought}
                        </p>
                      </div>
                    )}

                    {task.output && (
                      <div className="space-y-1 pt-1">
                        <div className="text-[11px] text-cyan-400/90 font-semibold">
                          Agent Intermediate Output:
                        </div>
                        <div className="bg-slate-900/80 p-2.5 rounded-lg border border-white/5 text-slate-300 text-[11px] whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed">
                          {task.output}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
