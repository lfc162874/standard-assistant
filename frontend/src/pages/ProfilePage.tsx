import { FormEvent, useState } from "react";

import type { UserProfile } from "../types/user";

interface ProfilePageProps {
  user: UserProfile;
  loading: boolean;
  error: string;
  success: string;
  onBack: () => void;
  onUpdateProfile: (payload: {
    nickname?: string | null;
    email?: string | null;
    phone?: string | null;
    avatar_url?: string | null;
  }) => Promise<void>;
  onChangePassword: (payload: { old_password: string; new_password: string }) => Promise<void>;
}

export default function ProfilePage({
  user,
  loading,
  error,
  success,
  onBack,
  onUpdateProfile,
  onChangePassword,
}: ProfilePageProps) {
  const [nickname, setNickname] = useState(user.nickname ?? "");
  const [email, setEmail] = useState(user.email ?? "");
  const [phone, setPhone] = useState(user.phone ?? "");
  const [avatarUrl, setAvatarUrl] = useState(user.avatar_url ?? "");

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");

  async function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onUpdateProfile({
      nickname: nickname.trim() || null,
      email: email.trim() || null,
      phone: phone.trim() || null,
      avatar_url: avatarUrl.trim() || null,
    });
  }

  async function submitPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError("");

    if (newPassword.length < 8) {
      setPasswordError("新密码至少 8 位");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("两次输入的新密码不一致");
      return;
    }

    await onChangePassword({
      old_password: oldPassword,
      new_password: newPassword,
    });

    setOldPassword("");
    setNewPassword("");
    setConfirmPassword("");
  }

  return (
    <main className="profile-shell">
      <section className="profile-card">
        <header className="profile-head">
          <h1>个人资料</h1>
          <button type="button" className="ghost-btn" onClick={onBack} disabled={loading}>
            返回聊天
          </button>
        </header>

        <p className="profile-meta">账号：{user.username} · 角色：{user.role}</p>

        <form className="profile-form" onSubmit={submitProfile}>
          <h2>基础信息</h2>

          <label htmlFor="profile-nickname">昵称</label>
          <input
            id="profile-nickname"
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
            disabled={loading}
          />

          <label htmlFor="profile-email">邮箱</label>
          <input
            id="profile-email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            type="email"
            disabled={loading}
          />

          <label htmlFor="profile-phone">手机号</label>
          <input
            id="profile-phone"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            disabled={loading}
          />

          <label htmlFor="profile-avatar">头像 URL</label>
          <input
            id="profile-avatar"
            value={avatarUrl}
            onChange={(event) => setAvatarUrl(event.target.value)}
            disabled={loading}
          />

          <button type="submit" className="auth-primary-btn" disabled={loading}>
            {loading ? "保存中..." : "保存资料"}
          </button>
        </form>

        <form className="profile-form" onSubmit={submitPassword}>
          <h2>修改密码</h2>

          <label htmlFor="profile-old-password">旧密码</label>
          <input
            id="profile-old-password"
            type="password"
            value={oldPassword}
            onChange={(event) => setOldPassword(event.target.value)}
            autoComplete="current-password"
            disabled={loading}
          />

          <label htmlFor="profile-new-password">新密码</label>
          <input
            id="profile-new-password"
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            autoComplete="new-password"
            disabled={loading}
          />

          <label htmlFor="profile-new-password-confirm">确认新密码</label>
          <input
            id="profile-new-password-confirm"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            autoComplete="new-password"
            disabled={loading}
          />

          {passwordError ? <div className="auth-error">{passwordError}</div> : null}

          <button type="submit" className="auth-primary-btn" disabled={loading}>
            {loading ? "提交中..." : "更新密码"}
          </button>
        </form>

        {error ? <div className="auth-error global">{error}</div> : null}
        {success ? <div className="auth-success">{success}</div> : null}
      </section>
    </main>
  );
}
