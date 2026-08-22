import React, { createContext, useContext, useEffect, useState } from 'react';
import { LoginPayload, User } from '../types/auth';
import { authService } from '../services/authService';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (user: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken =
        localStorage.getItem('apnaerp_access_token') ||
        sessionStorage.getItem('apnaerp_access_token');

      if (storedToken) {
        setToken(storedToken);
        try {
          const userProfile = await authService.getCurrentUser();
          setUser(userProfile);
        } catch {
          // Token invalid, clear state
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (payload: LoginPayload) => {
    setIsLoading(true);
    try {
      const { tokens, user: authUser } = await authService.login(payload);
      
      const storage = payload.remember_me !== false ? localStorage : sessionStorage;
      storage.setItem('apnaerp_access_token', tokens.access_token);
      if (tokens.refresh_token) {
        storage.setItem('apnaerp_refresh_token', tokens.refresh_token);
      }
      storage.setItem('apnaerp_user_profile', JSON.stringify(authUser));

      setToken(tokens.access_token);
      setUser(authUser);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authService.logout();
    } finally {
      setToken(null);
      setUser(null);
      setIsLoading(false);
    }
  };

  const updateUser = (updatedFields: Partial<User>) => {
    if (!user) return;
    const updated = { ...user, ...updatedFields };
    setUser(updated);
    if (localStorage.getItem('apnaerp_user_profile')) {
      localStorage.setItem('apnaerp_user_profile', JSON.stringify(updated));
    } else {
      sessionStorage.setItem('apnaerp_user_profile', JSON.stringify(updated));
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        logout,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
