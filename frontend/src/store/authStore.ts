import type { UserProfile } from "../types/user";

const REFRESH_TOKEN_KEY = "auth_refresh_token";

type Listener = () => void;

export interface AuthSnapshot {
  initialized: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  user: UserProfile | null;
}

let snapshot: AuthSnapshot = {
  initialized: false,
  accessToken: null,
  refreshToken: null,
  user: null,
};

const listeners = new Set<Listener>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

function readRefreshTokenFromStorage(): string | null {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeRefreshTokenToStorage(value: string | null): void {
  try {
    if (!value) {
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      return;
    }
    localStorage.setItem(REFRESH_TOKEN_KEY, value);
  } catch {
    // Ignore storage failures in private mode.
  }
}

export function subscribeAuthStore(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getAuthSnapshot(): AuthSnapshot {
  return snapshot;
}

export function bootstrapRefreshToken(): void {
  snapshot = {
    ...snapshot,
    refreshToken: readRefreshTokenFromStorage(),
  };
  emit();
}

export function setAuthInitialized(initialized: boolean): void {
  snapshot = {
    ...snapshot,
    initialized,
  };
  emit();
}

export function setAccessToken(accessToken: string | null): void {
  snapshot = {
    ...snapshot,
    accessToken,
  };
  emit();
}

export function setRefreshToken(refreshToken: string | null): void {
  writeRefreshTokenToStorage(refreshToken);
  snapshot = {
    ...snapshot,
    refreshToken,
  };
  emit();
}

export function setCurrentUser(user: UserProfile | null): void {
  snapshot = {
    ...snapshot,
    user,
  };
  emit();
}

export function applyAuthSession(payload: {
  accessToken: string;
  refreshToken: string;
  user: UserProfile;
}): void {
  writeRefreshTokenToStorage(payload.refreshToken);
  snapshot = {
    ...snapshot,
    accessToken: payload.accessToken,
    refreshToken: payload.refreshToken,
    user: payload.user,
  };
  emit();
}

export function clearAuthSession(): void {
  writeRefreshTokenToStorage(null);
  snapshot = {
    ...snapshot,
    accessToken: null,
    refreshToken: null,
    user: null,
  };
  emit();
}
