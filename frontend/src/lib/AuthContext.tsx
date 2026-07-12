"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { User, fetchCurrentUser, login as apiLogin, logout as apiLogout } from "./api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refetchUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const router = useRouter();

  const refetchUser = async () => {
    try {
      const currentUser = await fetchCurrentUser();
      setUser(currentUser);
    } catch (err: any) {
      console.error("fetchCurrentUser failed:", err);
      if (typeof window !== "undefined") {
        sessionStorage.setItem("last_auth_error", err.message || err.toString());
        localStorage.removeItem("auth_token");
      }
      try {
        await apiLogout(); // clear the invalid HttpOnly cookie via the backend
      } catch (err) {
        // ignore logout errors
      }
      if (typeof window !== "undefined" && window.location.pathname !== "/login" && window.location.pathname !== "/") {
        router.push("/login");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refetchUser();
  }, []);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const loggedUser = await apiLogin(email, password);
      setUser(loggedUser);
      if (typeof window !== "undefined" && loggedUser.token) {
        localStorage.setItem("auth_token", loggedUser.token);
      }
      window.location.href = "/dashboard";
    } catch (err) {
      setUser(null);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      await apiLogout();
      setUser(null);
      if (typeof window !== "undefined") {
        localStorage.removeItem("auth_token");
      }
      window.location.href = "/login";
    } catch (err) {
      console.error("Failed to log out:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refetchUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
