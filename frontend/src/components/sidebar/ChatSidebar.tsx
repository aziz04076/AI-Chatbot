import React, { useState, useEffect } from 'react';
import { Plus, MessageSquare, Trash2, FileDown, Activity, Settings2, LogOut, ChevronRight, Cpu } from 'lucide-react';
import { ConversationSummary } from '../../types';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface ChatSidebarProps {
  currentSessionId: string;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onOpenDashboard: () => void;
  onOpenSettings: () => void;
  isOpen: boolean;
  onClose: () => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  currentSessionId,
  onSelectSession,
  onNewSession,
  onOpenDashboard,
  onOpenSettings,
  isOpen,
  onClose,
}) => {
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState<ConversationSummary[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('nexus-llama3-8b-v1');

  useEffect(() => {
    loadSessions();
    loadModels();
  }, [currentSessionId]);

  const loadSessions = async () => {
    try {
      const data = await api.getConversations();
      setSessions(data);
    } catch {}
  };

  const loadModels = async () => {
    try {
      const data = await api.getModels();
      setModels(data.available_models);
      setSelectedModel(data.current_model);
    } catch {}
  };

  const handleModelChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModel = e.target.value;
    setSelectedModel(newModel);
    try {
      await api.switchModel(newModel);
    } catch {}
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await api.deleteConversation(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (id === currentSessionId) {
        onNewSession();
      }
    } catch {}
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 lg:hidden"
        />
      )}

      <aside
        className={`fixed lg:static top-0 left-0 h-full w-72 sm:w-80 glass-header border-r border-white/10 z-40 flex flex-col transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Sidebar Header */}
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-400 to-indigo-500 flex items-center justify-center text-black font-extrabold text-sm shadow-[0_0_15px_rgba(0,242,254,0.3)]">
              Ω
            </div>
            <div>
              <div className="font-bold text-sm tracking-wide text-white">NexusAI</div>
              <div className="text-[10px] font-mono text-cyan-400">Enterprise Cloud SRE</div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden p-1.5 rounded-lg hover:bg-white/10 text-slate-400"
          >
            ✕
          </button>
        </div>

        {/* New Session Action */}
        <div className="p-3">
          <button
            onClick={() => {
              onNewSession();
              if (window.innerWidth < 1024) onClose();
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500/20 to-blue-500/20 hover:from-cyan-500/30 hover:to-blue-500/30 border border-cyan-500/30 text-cyan-300 font-semibold text-xs tracking-wide transition-all shadow-sm"
          >
            <Plus className="w-4 h-4 text-cyan-400" />
            <span>New Architecture Session</span>
          </button>
        </div>

        {/* Model Checkpoint Switcher */}
        <div className="px-3 pb-2">
          <div className="p-2.5 rounded-xl bg-slate-900/60 border border-white/5 space-y-1.5">
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400">
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              <span>Model Checkpoint</span>
            </div>
            <select
              value={selectedModel}
              onChange={handleModelChange}
              className="w-full bg-slate-950 text-xs text-cyan-300 border border-slate-700/60 rounded-lg p-1.5 focus:outline-none focus:border-cyan-500"
            >
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Session History List */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
          <div className="text-[11px] font-mono tracking-wider text-slate-500 uppercase px-2 mb-2">
            Archived Consultations
          </div>
          {sessions.length === 0 ? (
            <div className="text-xs text-slate-500 text-center py-6">No previous sessions found</div>
          ) : (
            sessions.map((s) => {
              const isActive = s.id === currentSessionId;
              return (
                <div
                  key={s.id}
                  onClick={() => {
                    onSelectSession(s.id);
                    if (window.innerWidth < 1024) onClose();
                  }}
                  className={`group flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-all ${
                    isActive
                      ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 shadow-sm'
                      : 'text-slate-400 hover:bg-white/5 hover:text-slate-200 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate mr-2">
                    <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-70" />
                    <span className="truncate">{s.title || 'Untitled Consultation'}</span>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, s.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 transition-opacity"
                    title="Delete session"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Export & Admin Nav */}
        <div className="p-3 border-t border-white/10 space-y-1 bg-slate-950/40">
          <div className="flex gap-2 mb-2">
            <a
              href={api.getExportUrl(currentSessionId, 'pdf')}
              download
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg bg-slate-900/80 hover:bg-slate-800 text-[11px] font-mono text-slate-300 border border-white/5 hover:border-cyan-500/30 transition-all"
            >
              <FileDown className="w-3.5 h-3.5 text-cyan-400" />
              <span>PDF</span>
            </a>
            <a
              href={api.getExportUrl(currentSessionId, 'text')}
              download
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg bg-slate-900/80 hover:bg-slate-800 text-[11px] font-mono text-slate-300 border border-white/5 hover:border-cyan-500/30 transition-all"
            >
              <FileDown className="w-3.5 h-3.5 text-blue-400" />
              <span>Text</span>
            </a>
          </div>

          <button
            onClick={() => {
              onOpenDashboard();
              if (window.innerWidth < 1024) onClose();
            }}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-300 hover:bg-white/5 hover:text-cyan-300 transition-all"
          >
            <Activity className="w-4 h-4 text-emerald-400" />
            <span>Admin Health & Analytics</span>
            <ChevronRight className="w-3.5 h-3.5 ml-auto text-slate-600" />
          </button>

          <button
            onClick={onOpenSettings}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-300 hover:bg-white/5 hover:text-cyan-300 transition-all"
          >
            <Settings2 className="w-4 h-4 text-purple-400" />
            <span>Theme & Visual Style</span>
          </button>
        </div>

        {/* User Profile / Logout */}
        <div className="p-3 border-t border-white/10 flex items-center justify-between bg-slate-950/70">
          <div className="truncate mr-2">
            <div className="text-xs font-semibold text-white truncate">{user?.username || 'Guest'}</div>
            <div className="text-[10px] font-mono text-slate-500 truncate">{user?.email || 'guest@nexus.ai'}</div>
          </div>
          <button
            onClick={logout}
            className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-rose-400 transition-colors"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>
    </>
  );
};
