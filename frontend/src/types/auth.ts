import type { UserProfile } from "./user";

export interface RegisterRequest {
  username: string;
  password: string;
  nickname?: string;
  email?: string;
  phone?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface LogoutRequest {
  refresh_token: string;
}

export interface AuthTokenResponse {
  access_token: string;
  access_expires_in: number;
  refresh_token: string;
  refresh_expires_in: number;
  user: UserProfile;
}

export interface PasswordChangeRequest {
  old_password: string;
  new_password: string;
}

export interface ProfileUpdateRequest {
  nickname?: string | null;
  email?: string | null;
  phone?: string | null;
  avatar_url?: string | null;
}

export interface OkResponse {
  ok: boolean;
}
