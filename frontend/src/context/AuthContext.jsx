import { createContext, useContext, useState } from "react";
import { loginAccount, registerAccount } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem("vayumesh_user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const login = async (email, password) => {
    const data = await loginAccount(email, password);
    setUser(data.user);
    return data;
  };

  const register = async (payload) => {
    const data = await registerAccount(payload);
    setUser(data.user);
    return data;
  };

  const logout = () => {
    localStorage.removeItem("vayumesh_token");
    localStorage.removeItem("vayumesh_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
