import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { api, setAuthToken, clearAuthToken, getAuthToken } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (u: string, p: string) => Promise<void>;
  register: (e: string, u: string, p: string) => Promise<void>;
  logout: () => void;
  continueAsGuest: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = getAuthToken();
      if (token) {
        try {
          const profile = await api.getMe();
          setUser(profile);
        } catch {
          clearAuthToken();
          setUser({ id: 'guest_user', username: 'Guest Operator', email: 'guest@nexus.ai', role: 'guest' });
        }
      } else {
        setUser({ id: 'guest_user', username: 'Guest Operator', email: 'guest@nexus.ai', role: 'guest' });
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = async (u: string, p: string) => {
    const data = await api.login(u, p);
    setAuthToken(data.access_token);
    setUser(data.user);
  };

  const register = async (e: string, u: string, p: string) => {
    const data = await api.register(e, u, p);
    setAuthToken(data.access_token);
    setUser(data.user);
  };

  const logout = () => {
    clearAuthToken();
    setUser({ id: 'guest_user', username: 'Guest Operator', email: 'guest@nexus.ai', role: 'guest' });
  };

  const continueAsGuest = () => {
    clearAuthToken();
    setUser({ id: 'guest_user', username: 'Guest Operator', email: 'guest@nexus.ai', role: 'guest' });
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: user?.role !== 'guest', isLoading, login, register, logout, continueAsGuest }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
