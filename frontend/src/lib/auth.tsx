"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import api from "@/lib/api";
import { AuthUser, AuthTokens } from "@/lib/types";

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (tokens: AuthTokens) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
  updateUser: (patch: Partial<AuthUser>) => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isLoading: true,
  login: () => {},
  logout: () => {},
  refreshUser: async () => {},
  updateUser: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Hydrate from localStorage
    const storedToken = localStorage.getItem("invox_access_token");
    const storedUser = localStorage.getItem("invox_user");
    if (storedToken && storedUser) {
      try {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
        api.defaults.headers.common["Authorization"] = `Bearer ${storedToken}`;
      } catch {
        localStorage.removeItem("invox_access_token");
        localStorage.removeItem("invox_user");
      }
    }
    setIsLoading(false);
  }, []);

  const login = (tokens: AuthTokens) => {
    setToken(tokens.access_token);
    setUser(tokens.user);
    localStorage.setItem("invox_access_token", tokens.access_token);
    localStorage.setItem("invox_refresh_token", tokens.refresh_token);
    localStorage.setItem("invox_user", JSON.stringify(tokens.user));
    api.defaults.headers.common["Authorization"] = `Bearer ${tokens.access_token}`;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("invox_access_token");
    localStorage.removeItem("invox_refresh_token");
    localStorage.removeItem("invox_user");
    delete api.defaults.headers.common["Authorization"];
  };

  const refreshUser = async () => {
    const refreshToken = localStorage.getItem("invox_refresh_token");
    if (!refreshToken) return;
    try {
      const r = await api.post("/auth/refresh", { refresh_token: refreshToken });
      login(r.data);
    } catch {
      logout();
    }
  };

  const updateUser = (patch: Partial<AuthUser>) => {
    setUser((prev) => {
      if (!prev) return prev;
      const updated = { ...prev, ...patch };
      localStorage.setItem("invox_user", JSON.stringify(updated));
      return updated;
    });
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout, refreshUser, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
