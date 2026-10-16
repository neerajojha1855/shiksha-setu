import { useEffect, useState } from "react";

import { AuthContent } from "./AuthContent";
import {
  getCurrentUser,
  loadAuth,
  login,
  logout,
  register,
  saveAuth,
  toAuthState,
  type AuthResponse,
  type AuthState,
} from "./auth-service";

export function AuthPage() {
  const [auth, setAuth] = useState<AuthState | null>(loadAuth);

  useEffect(() => {
    if (!auth) {
      return;
    }
    getCurrentUser(auth.accessToken).catch(() => {
      setAuth(null);
      saveAuth(null);
    });
  }, [auth]);

  function handleAuthenticated(response: AuthResponse): void {
    const nextAuth = toAuthState(response);
    setAuth(nextAuth);
    saveAuth(nextAuth);
  }

  async function handleLogout(): Promise<void> {
    if (auth) {
      await logout(auth.refreshToken).catch(() => undefined);
    }
    setAuth(null);
    saveAuth(null);
  }

  return (
    <AuthContent
      auth={auth}
      onAuthenticated={handleAuthenticated}
      onLogout={handleLogout}
      onLogin={login}
      onRegister={register}
    />
  );
}
