import { createContext, useContext, useMemo, useState } from "react";

const AuthContext = createContext(null);

const TOKEN_KEY = "vyaparSathiAuthToken";
const EMAIL_KEY = "vyaparSathiAuthEmail";
const ROLE_KEY = "vyaparSathiAuthRole";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [email, setEmail] = useState(() => localStorage.getItem(EMAIL_KEY));
  const [role, setRole] = useState(() => localStorage.getItem(ROLE_KEY) || "owner");

  const value = useMemo(
    () => ({
      token,
      email,
      role,
      isAuthenticated: Boolean(token),
      login: (nextToken, nextEmail, nextRole = "owner") => {
        localStorage.setItem(TOKEN_KEY, nextToken);
        localStorage.setItem(EMAIL_KEY, nextEmail);
        localStorage.setItem(ROLE_KEY, nextRole);
        setToken(nextToken);
        setEmail(nextEmail);
        setRole(nextRole);
      },
      logout: () => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(EMAIL_KEY);
        localStorage.removeItem(ROLE_KEY);
        setToken(null);
        setEmail(null);
        setRole(null);
      },
    }),
    [token, email, role]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
