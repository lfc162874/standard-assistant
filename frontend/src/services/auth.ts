import {
  applyAuthSession,
  bootstrapRefreshToken,
  clearAuthSession,
  getAuthSnapshot,
  setAccessToken,
  setAuthInitialized,
  setCurrentUser,
  setRefreshToken,
} from "../store/authStore";
import type {
  AuthTokenResponse,
  LoginRequest,
  LogoutRequest,
  PasswordChangeRequest,
  ProfileUpdateRequest,
  RefreshRequest,
  RegisterRequest,
} from "../types/auth";
import type { UserProfile } from "../types/user";
import { ApiError, buildUrl, parseError } from "./http";

let refreshInFlight: Promise<boolean> | null = null;
let bootstrapInFlight: Promise<void> | null = null;

function mergeHeaders(initHeaders?: HeadersInit, hasFormData = false): Headers {
  const headers = new Headers(initHeaders ?? {});
  if (!hasFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return headers;
}

async function postJson<TResponse, TRequest>(path: string, payload: TRequest): Promise<TResponse> {
  const response = await fetch(buildUrl(path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    await parseError(response);
  }

  return (await response.json()) as TResponse;
}

function applyTokenResponse(data: AuthTokenResponse): AuthTokenResponse {
  applyAuthSession({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    user: data.user,
  });
  return data;
}

export async function register(payload: RegisterRequest): Promise<UserProfile> {
  return postJson<UserProfile, RegisterRequest>("/api/v1/auth/register", payload);
}

export async function login(payload: LoginRequest): Promise<AuthTokenResponse> {
  const data = await postJson<AuthTokenResponse, LoginRequest>("/api/v1/auth/login", payload);
  return applyTokenResponse(data);
}

export async function refreshAuthToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;

  const refreshToken = getAuthSnapshot().refreshToken;
  if (!refreshToken) return false;

  refreshInFlight = (async () => {
    try {
      const data = await postJson<AuthTokenResponse, RefreshRequest>("/api/v1/auth/refresh", {
        refresh_token: refreshToken,
      });
      applyTokenResponse(data);
      return true;
    } catch {
      clearAuthSession();
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

export async function logout(): Promise<void> {
  const refreshToken = getAuthSnapshot().refreshToken;
  if (refreshToken) {
    try {
      await postJson<{ ok: boolean }, LogoutRequest>("/api/v1/auth/logout", {
        refresh_token: refreshToken,
      });
    } catch {
      // Ignore logout transport errors and clear local auth state anyway.
    }
  }

  clearAuthSession();
  setAuthInitialized(true);
}

async function authFetch(path: string, init?: RequestInit, allowRetry = true): Promise<Response> {
  const token = getAuthSnapshot().accessToken;
  if (!token) {
    throw new ApiError(401, "未登录或登录已过期");
  }

  const headers = mergeHeaders(init?.headers, init?.body instanceof FormData);
  headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(buildUrl(path), {
    ...init,
    headers,
  });

  if (response.status === 401 && allowRetry) {
    const refreshed = await refreshAuthToken();
    if (!refreshed) {
      throw new ApiError(401, "登录已过期，请重新登录");
    }
    return authFetch(path, init, false);
  }

  return response;
}

export async function authJsonFetch(path: string, init?: RequestInit): Promise<Response> {
  const response = await authFetch(path, init, true);
  if (!response.ok) {
    await parseError(response);
  }
  return response;
}

export async function authRequestFetch(path: string, init?: RequestInit): Promise<Response> {
  const response = await authFetch(path, init, true);
  if (!response.ok) {
    await parseError(response);
  }
  return response;
}

export async function getMe(): Promise<UserProfile> {
  const response = await authJsonFetch("/api/v1/users/me", {
    method: "GET",
  });
  const profile = (await response.json()) as UserProfile;
  setCurrentUser(profile);
  return profile;
}

export async function updateMe(payload: ProfileUpdateRequest): Promise<UserProfile> {
  const response = await authJsonFetch("/api/v1/users/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  const profile = (await response.json()) as UserProfile;
  setCurrentUser(profile);
  return profile;
}

export async function changeMyPassword(payload: PasswordChangeRequest): Promise<void> {
  await authJsonFetch("/api/v1/users/me/password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function bootstrapAuthSession(): Promise<void> {
  if (bootstrapInFlight) return bootstrapInFlight;

  bootstrapInFlight = (async () => {
    bootstrapRefreshToken();
    if (!getAuthSnapshot().refreshToken) {
      setAuthInitialized(true);
      return;
    }

    const refreshed = await refreshAuthToken();
    if (refreshed) {
      await getMe();
    } else {
      clearAuthSession();
      setAccessToken(null);
      setRefreshToken(null);
    }
    setAuthInitialized(true);
  })();

  try {
    await bootstrapInFlight;
  } finally {
    bootstrapInFlight = null;
  }
}
