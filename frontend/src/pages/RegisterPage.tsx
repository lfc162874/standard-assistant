import { FormEvent, useState } from "react";

interface RegisterPageProps {
  loading: boolean;
  error: string;
  onSubmit: (payload: {
    username: string;
    password: string;
    nickname?: string;
    email?: string;
    phone?: string;
  }) => Promise<void>;
  onSwitchToLogin: () => void;
}

export default function RegisterPage({
  loading,
  error,
  onSubmit,
  onSwitchToLogin,
}: RegisterPageProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [localError, setLocalError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError("");

    if (!username.trim()) {
      setLocalError("用户名不能为空");
      return;
    }

    if (password.length < 8) {
      setLocalError("密码至少 8 位");
      return;
    }

    if (password !== confirmPassword) {
      setLocalError("两次输入的密码不一致");
      return;
    }

    await onSubmit({
      username: username.trim(),
      password,
      nickname: nickname.trim() || undefined,
      email: email.trim() || undefined,
      phone: phone.trim() || undefined,
    });
  }

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-label="注册表单">
        <h1>注册新账号</h1>
        <p className="auth-sub">创建后可直接登录并进入个人空间。</p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="register-username">用户名</label>
          <input
            id="register-username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            disabled={loading}
            placeholder="3-64 位字符"
          />

          <label htmlFor="register-password">密码</label>
          <input
            id="register-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            disabled={loading}
            placeholder="至少 8 位"
          />

          <label htmlFor="register-password-confirm">确认密码</label>
          <input
            id="register-password-confirm"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            autoComplete="new-password"
            disabled={loading}
            placeholder="再次输入密码"
          />

          <label htmlFor="register-nickname">昵称（可选）</label>
          <input
            id="register-nickname"
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
            disabled={loading}
            placeholder="展示名称"
          />

          <label htmlFor="register-email">邮箱（可选）</label>
          <input
            id="register-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            disabled={loading}
            placeholder="name@example.com"
          />

          <label htmlFor="register-phone">手机号（可选）</label>
          <input
            id="register-phone"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            autoComplete="tel"
            disabled={loading}
            placeholder="用于联系"
          />

          {localError || error ? <div className="auth-error">{localError || error}</div> : null}

          <button type="submit" className="auth-primary-btn" disabled={loading}>
            {loading ? "注册中..." : "注册"}
          </button>
        </form>

        <button type="button" className="auth-link-btn" onClick={onSwitchToLogin} disabled={loading}>
          已有账号？去登录
        </button>
      </section>
    </main>
  );
}
