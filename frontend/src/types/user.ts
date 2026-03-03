export interface UserProfile {
  id: string;
  username: string;
  nickname: string | null;
  email: string | null;
  phone: string | null;
  avatar_url: string | null;
  role: string;
  status: string;
  created_at: string;
  last_login_at: string | null;
}
