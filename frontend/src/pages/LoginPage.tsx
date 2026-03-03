import { FormEvent, useState } from "react";

interface LoginPageProps {
  loading: boolean;
  error: string;
  success: string;
  onSubmit: (payload: { username: string; password: string }) => Promise<void>;
  onSwitchToRegister: () => void;
}

export default function LoginPage({
  loading,
  error,
  success,
  onSubmit,
  onSwitchToRegister,
}: LoginPageProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [localError, setLocalError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError("");

    if (!username.trim() || !password.trim()) {
      setLocalError("请输入用户名和密码");
      return;
    }

    await onSubmit({
      username: username.trim(),
      password,
    });
  }

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-label="登录表单">
        <h1>登录标准智能助手</h1>
        <p className="auth-sub">登录后可使用会话记忆、资料管理与受保护接口。</p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="login-username">用户名</label>
          <input
            id="login-username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            disabled={loading}
            placeholder="请输入用户名"
          />

          <label htmlFor="login-password">密码</label>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            disabled={loading}
            placeholder="请输入密码"
          />

          {localError || error ? <div className="auth-error">{localError || error}</div> : null}
          {success ? <div className="auth-success">{success}</div> : null}

          <button type="submit" className="auth-primary-btn" disabled={loading}>
            {loading ? "登录中..." : "登录"}
          </button>
        </form>

        <button type="button" className="auth-link-btn" onClick={onSwitchToRegister} disabled={loading}>
          还没有账号？去注册
        </button>
      </section>
    </main>
  );
}
