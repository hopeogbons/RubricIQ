import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  api,
  getStoredToken,
  setStoredToken,
  setUnauthorizedHandler,
} from "@/lib/api";

export type Role = "superadmin" | "admin" | "evaluator" | "viewer";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: Role;
  is_active: boolean;
  activated_at: string | null;
  created_at: string;
}

interface LoginPayload {
  email: string;
  password: string;
}

export interface SignupPayload {
  email: string;
  password: string;
  full_name?: string;
}

export type AuthStatus = "loading" | "anonymous" | "authenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: User | null;
  login: (payload: LoginPayload) => Promise<User>;
  logout: () => void;
  signup: (payload: SignupPayload) => Promise<User>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }): JSX.Element {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  const clearSession = useCallback(() => {
    setStoredToken(null);
    setUser(null);
    setStatus("anonymous");
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setStatus("anonymous");
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const token = getStoredToken();
    if (!token) {
      setStatus("anonymous");
      return;
    }
    api
      .get<User>("/auth/me")
      .then((res) => {
        if (cancelled) return;
        setUser(res.data);
        setStatus("authenticated");
      })
      .catch(() => {
        if (cancelled) return;
        setStoredToken(null);
        setUser(null);
        setStatus("anonymous");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async ({ email, password }: LoginPayload): Promise<User> => {
    const tokenResp = await api.post<{ access_token: string; token_type: string }>(
      "/auth/login",
      { email, password },
    );
    setStoredToken(tokenResp.data.access_token);
    const meResp = await api.get<User>("/auth/me");
    setUser(meResp.data);
    setStatus("authenticated");
    return meResp.data;
  }, []);

  const signup = useCallback(async (payload: SignupPayload): Promise<User> => {
    const resp = await api.post<User>("/auth/signup", payload);
    return resp.data;
  }, []);

  const logout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, login, logout, signup }),
    [status, user, login, logout, signup],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
