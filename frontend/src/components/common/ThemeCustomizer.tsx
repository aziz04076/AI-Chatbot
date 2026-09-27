import React from 'react';
import { Palette, Check, X } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { ThemeStyle } from '../../types';

interface ThemeCustomizerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ThemeCustomizer: React.FC<ThemeCustomizerProps> = ({ isOpen, onClose }) => {
  const { theme, setTheme } = useTheme();

  if (!isOpen) return null;

  const themes: Array<{ id: ThemeStyle; name: string; desc: string; colors: string[] }> = [
    {
      id: 'cyberpunk',
      name: 'Cyberpunk Neon',
      desc: 'High-octane neon cyan & electric pink on obsidian glass',
      colors: ['#00f2fe', '#4facfe', '#ff0080'],
    },
    {
      id: 'cosmic',
      name: 'Cosmic Nebula',
      desc: 'Deep gravitational violet, starry indigo, and supernova glow',
      colors: ['#8b5cf6', '#6366f1', '#ec4899'],
    },
    {
      id: 'minimal',
      name: 'Minimal Slate',
      desc: 'Clean architectural monochrome with icy platinum highlights',
      colors: ['#38bdf8', '#64748b', '#cbd5e1'],
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md">
      <div className="w-full max-w-md glass-panel border border-purple-500/40 rounded-3xl overflow-hidden shadow-2xl animate-fadeIn">
        <div className="p-5 border-b border-white/10 flex items-center justify-between glass-header">
          <div className="flex items-center gap-2.5">
            <Palette className="w-5 h-5 text-purple-400" />
            <h3 className="text-base font-bold text-white">Visual Style Customizer</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-3">
          {themes.map((t) => {
            const isSelected = theme === t.id;
            return (
              <div
                key={t.id}
                onClick={() => setTheme(t.id)}
                className={`p-4 rounded-2xl cursor-pointer border transition-all ${
                  isSelected
                    ? 'bg-purple-500/20 border-purple-500/50 shadow-lg'
                    : 'bg-slate-900/60 border-white/5 hover:border-white/20'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="font-semibold text-sm text-white">{t.name}</div>
                  {isSelected && <Check className="w-4 h-4 text-purple-400" />}
                </div>
                <div className="text-xs text-slate-400 mb-3">{t.desc}</div>
                <div className="flex gap-1.5">
                  {t.colors.map((c, i) => (
                    <div
                      key={i}
                      className="w-6 h-6 rounded-full border border-white/20 shadow-sm"
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
