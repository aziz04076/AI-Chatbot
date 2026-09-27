import React, { useState, useEffect } from 'react';
import { Search, Plus, Activity, Palette, FileDown, LogOut, Terminal, X } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNewSession: () => void;
  onOpenDashboard: () => void;
  currentSessionId: string;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNewSession,
  onOpenDashboard,
  currentSessionId,
}) => {
  const [query, setQuery] = useState('');
  const { setTheme } = useTheme();
  const { logout } = useAuth();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else setQuery('');
      } else if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const actions = [
    {
      id: 'new_chat',
      title: 'New Architecture Session',
      desc: 'Start a fresh consultation context',
      icon: Plus,
      run: () => {
        onNewSession();
        onClose();
      },
    },
    {
      id: 'analytics',
      title: 'Open System Health Dashboard',
      desc: 'Inspect real-time GPU VRAM, latency & usage',
      icon: Activity,
      run: () => {
        onOpenDashboard();
        onClose();
      },
    },
    {
      id: 'theme_cyberpunk',
      title: 'Visual Theme: Cyberpunk Neon',
      desc: 'Switch to high-contrast cyan & magenta',
      icon: Palette,
      run: () => {
        setTheme('cyberpunk');
        onClose();
      },
    },
    {
      id: 'theme_cosmic',
      title: 'Visual Theme: Cosmic Nebula',
      desc: 'Switch to deep indigo & violet palette',
      icon: Palette,
      run: () => {
        setTheme('cosmic');
        onClose();
      },
    },
    {
      id: 'theme_minimal',
      title: 'Visual Theme: Minimal Slate',
      desc: 'Switch to clean monochrome frosted glass',
      icon: Palette,
      run: () => {
        setTheme('minimal');
        onClose();
      },
    },
    {
      id: 'export_pdf',
      title: 'Export Consultation as PDF',
      desc: 'Download high-resolution audit PDF',
      icon: FileDown,
      run: () => {
        window.open(api.getExportUrl(currentSessionId, 'pdf'), '_blank');
        onClose();
      },
    },
    {
      id: 'sign_out',
      title: 'Sign Out / Switch Operator',
      desc: 'Clear local session credentials',
      icon: LogOut,
      run: () => {
        logout();
        onClose();
      },
    },
  ];

  const filtered = actions.filter(
    (a) =>
      a.title.toLowerCase().includes(query.toLowerCase()) ||
      a.desc.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 p-4 bg-black/70 backdrop-blur-md">
      <div className="w-full max-w-xl glass-panel border border-cyan-500/40 rounded-2xl overflow-hidden shadow-2xl animate-fadeIn">
        <div className="p-3 border-b border-white/10 flex items-center gap-3 bg-slate-900/80">
          <Search className="w-4 h-4 text-cyan-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or action (e.g. 'export', 'dashboard', 'theme')..."
            autoFocus
            className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none"
          />
          <span className="text-[10px] font-mono text-slate-500 bg-slate-800 px-2 py-0.5 rounded border border-white/5">
            ESC
          </span>
        </div>

        <div className="max-h-72 overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-500 font-mono">No matching commands found</div>
          ) : (
            filtered.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={item.run}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-cyan-500/10 hover:border-cyan-500/30 border border-transparent text-left transition-all group"
                >
                  <div className="p-2 rounded-lg bg-slate-800 text-cyan-400 group-hover:bg-cyan-500/20 group-hover:text-cyan-300 transition-colors">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-white group-hover:text-cyan-200">
                      {item.title}
                    </div>
                    <div className="text-[11px] text-slate-400">{item.desc}</div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
