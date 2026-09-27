import React, { createContext, useContext, useState, useEffect } from 'react';
import { ThemeStyle } from '../types';

interface ThemeContextType {
  theme: ThemeStyle;
  setTheme: (theme: ThemeStyle) => void;
  accentColor: string;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemeStyle>(() => {
    return (localStorage.getItem('nexus_theme') as ThemeStyle) || 'cyberpunk';
  });

  const setTheme = (newTheme: ThemeStyle) => {
    setThemeState(newTheme);
    localStorage.setItem('nexus_theme', newTheme);
  };

  const getAccentColor = (): string => {
    switch (theme) {
      case 'cosmic':
        return '#8b5cf6'; // Indigo/Purple
      case 'minimal':
        return '#38bdf8'; // Sky/Platinum
      case 'cyberpunk':
      default:
        return '#00f2fe'; // Neon Cyan
    }
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, accentColor: getAccentColor() }}>
      <div className={`theme-${theme} min-h-screen text-slate-100`}>
        {children}
      </div>
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within a ThemeProvider');
  return context;
};
