import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authAPI } from '../utils/api';

interface User {
  id: string;
  email: string;
  username: string;
  name: string;
  created_at: string;
  preferred_language?: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, name: string, password: string, password_confirm: string, preferred_language?: string) => Promise<void>;
  updateProfile?: (data: any) => Promise<void>;
  googleLogin: (credential: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
  isFirstTimeLogin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isFirstTimeLogin, setIsFirstTimeLogin] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      authAPI.getProfile()
        .then(response => {
          setUser(response.data);
        })
        .catch(() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    const response = await authAPI.login(email, password);
    const { user, access, refresh } = response.data;
    
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    setUser(user);
    setIsFirstTimeLogin(true); // Mark as first-time login
  };

  const register = async (email: string, username: string, name: string, password: string, password_confirm: string, preferred_language?: string) => {
    const response = await authAPI.register(email, username, name, password, password_confirm, preferred_language);
    const { user, access, refresh } = response.data;
    
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    setUser(user);
    setIsFirstTimeLogin(true); // Mark as first-time login for new registrations
  };

  const googleLogin = async (credential: string) => {
    const response = await authAPI.googleAuth(credential);
    const { user, access, refresh } = response.data;
    
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    setUser(user);
    setIsFirstTimeLogin(true); // Mark as first-time login
  };

  const updateProfile = async (data: any) => {
    const response = await authAPI.updateProfile(data);
    setUser(response.data);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  const value = {
    user,
    login,
    register,
    googleLogin,
    logout,
    loading,
    updateProfile,
    isFirstTimeLogin,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};