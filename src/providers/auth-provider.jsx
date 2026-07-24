import { createContext, useContext, useMemo, useState } from "react";

const AuthContext = createContext(null);

const TOKEN_KEY = "vyaparSathiAuthToken";
const EMAIL_KEY = "vyaparSathiAuthEmail";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [email, setEmail] = useState(() => localStorage.getItem(EMAIL_KEY));

  const value = useMemo(
    () => ({
      token,
      email,
      isAuthenticated: Boolean(token),
      login: (nextToken, nextEmail) => {
        localStorage.setItem(TOKEN_KEY, nextToken);
        localStorage.setItem(EMAIL_KEY, nextEmail);
        setToken(nextToken);
        setEmail(nextEmail);
      },
      logout: () => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(EMAIL_KEY);
        setToken(null);
        setEmail(null);
      },
    }),
    [token, email]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
