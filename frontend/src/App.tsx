import { ChangeEvent, FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import MarkdownContent from "./components/MarkdownContent";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";
import { bootstrapAuthSession, changeMyPassword, login, logout, register, updateMe } from "./services/auth";
import { getHealth, getModels, postChatStream, postUploadTextFile } from "./services/api";
import { getAuthSnapshot, subscribeAuthStore } from "./store/authStore";
import type { ChatResponse, ModelOption, UploadTextResponse } from "./types/chat";
import { ApiError } from "./services/http";
import "./styles.css";

type ChatMessage =
  | { id: string; role: "user"; content: string }
  | {
      id: string;
      role: "assistant";
      content: string;
      result?: ChatResponse;
      streaming?: boolean;
    }
  | { id: string; role: "system"; content: string };

const SESSION_KEY = "standard_assistant_session_id";

type BackendStatus = "checking" | "online" | "offline";
type UploadStage = "idle" | "uploading" | "processing";

function getOrCreateSessionId(): string {
  const existing = localStorage.getItem(SESSION_KEY);
  if (existing) return existing;

  const generated = `session_${Math.random().toString(36).slice(2, 10)}`;
  localStorage.setItem(SESSION_KEY, generated);
  return generated;
}

function createNewSessionId(): string {
  const generated = `session_${Math.random().toString(36).slice(2, 10)}`;
  localStorage.setItem(SESSION_KEY, generated);
  return generated;
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;
  return date.toLocaleString("zh-CN", { hour12: false });
}

const QUICK_QUESTIONS = [
  "GB/T 19001 标准主要内容是什么？",
  "GB/T 19001 最新版和旧版有什么差异？",
  "ISO 9001 当前状态和适用范围是什么？",
];

type ComposerToolId = "assistant" | "thinking" | "research" | "code" | "image" | "more";

interface ComposerTool {
  id: ComposerToolId;
  label: string;
  seedText: string;
}

const COMPOSER_TOOLS: ComposerTool[] = [
  { id: "assistant", label: "任务助理", seedText: "请作为任务助理，帮我处理以下内容：\n" },
  { id: "thinking", label: "深度思考", seedText: "请从多个角度深入思考并分析：\n" },
  { id: "research", label: "深度研究", seedText: "请进行深入研究并给出结论：\n" },
  { id: "code", label: "代码", seedText: "请用代码实现并解释：\n" },
  { id: "image", label: "图像", seedText: "请结合图像相关场景处理：\n" },
  { id: "more", label: "更多", seedText: "请继续补充更多细节：\n" },
];

function renderComposerToolIcon(id: ComposerToolId) {
  if (id === "assistant") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2.5a1 1 0 0 1 1 1v3.07l2.76-1.6a1 1 0 1 1 1 1.73L14 8.3l2.76 1.6a1 1 0 1 1-1 1.73L13 10.03V13a1 1 0 1 1-2 0v-2.97l-2.76 1.6a1 1 0 1 1-1-1.73L10 8.3 7.24 6.7a1 1 0 1 1 1-1.73L11 6.57V3.5a1 1 0 0 1 1-1zM4.5 15a1 1 0 0 1 1 1v.5h.5a1 1 0 1 1 0 2h-.5v.5a1 1 0 1 1-2 0v-.5H3a1 1 0 1 1 0-2h.5V16a1 1 0 0 1 1-1zm15 1a1 1 0 0 1 1 1v.5h.5a1 1 0 1 1 0 2h-.5v.5a1 1 0 1 1-2 0v-.5H18a1 1 0 1 1 0-2h.5V17a1 1 0 0 1 1-1z" />
      </svg>
    );
  }
  if (id === "thinking") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 3a9 9 0 1 1-9 9 1 1 0 1 1 2 0 7 7 0 1 0 2.05-4.95 1 1 0 0 1-1.41-1.42A8.96 8.96 0 0 1 12 3zm.2 4a1 1 0 0 1 1 1v3.38l2.4 1.39a1 1 0 1 1-1 1.73l-2.9-1.68a1 1 0 0 1-.5-.87V8a1 1 0 0 1 1-1z" />
      </svg>
    );
  }
  if (id === "research") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M10.5 3a7.5 7.5 0 1 1-4.9 13.18l-2.9 2.9a1 1 0 1 1-1.4-1.42l2.9-2.9A7.5 7.5 0 0 1 10.5 3zm0 2a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11zm8.8 11.3a1 1 0 0 1 .7 1.23l-1.2 4a1 1 0 0 1-1.9-.57l.26-.86-1.78-.52a1 1 0 0 1 .56-1.92l1.8.52.25-.87a1 1 0 0 1 1.3-.67z" />
      </svg>
    );
  }
  if (id === "code") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M8.7 7.3a1 1 0 0 1 0 1.4L5.4 12l3.3 3.3a1 1 0 1 1-1.4 1.4l-4-4a1 1 0 0 1 0-1.4l4-4a1 1 0 0 1 1.4 0zm6.6 0a1 1 0 0 1 1.4 0l4 4a1 1 0 0 1 0 1.4l-4 4a1 1 0 1 1-1.4-1.4l3.3-3.3-3.3-3.3a1 1 0 0 1 0-1.4zM12.9 4a1 1 0 0 1 .98 1.2l-2 14a1 1 0 1 1-1.98-.28l2-14A1 1 0 0 1 12.9 4z" />
      </svg>
    );
  }
  if (id === "image") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 4a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h14a3 3 0 0 0 3-3V7a3 3 0 0 0-3-3H5zm0 2h14a1 1 0 0 1 1 1v7.17l-3.3-3.3a1 1 0 0 0-1.4 0L10 16.17l-1.3-1.3a1 1 0 0 0-1.4 0L4 18.17V7a1 1 0 0 1 1-1zm12 3a2 2 0 1 1-4 0 2 2 0 0 1 4 0z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 6a1 1 0 0 1 1-1h14a1 1 0 1 1 0 2H5a1 1 0 0 1-1-1zm0 6a1 1 0 0 1 1-1h9a1 1 0 1 1 0 2H5a1 1 0 0 1-1-1zm1 5a1 1 0 1 0 0 2h14a1 1 0 1 0 0-2H5z" />
    </svg>
  );
}

function createMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function messageTitle(message: ChatMessage, fallbackAssistantName: string): string {
  if (message.role === "assistant") {
    return readModelName(message.result) || fallbackAssistantName;
  }
  if (message.role === "user") return "你";
  return "系统提示";
}

function readModelName(result?: ChatResponse): string {
  if (!result) return "";
  const raw = result.data?.["model_name"];
  if (typeof raw === "string" && raw.trim()) return raw.trim();
  return "";
}

function readRetrievedCount(result?: ChatResponse): number {
  if (!result) return 0;
  const raw = result.data?.["retrieved_count"];
  if (typeof raw === "number") return raw;
  return 0;
}

function statusLabel(status: BackendStatus): string {
  if (status === "online") return "在线";
  if (status === "offline") return "离线";
  return "检测中";
}

function readCitationCodes(result?: ChatResponse): string[] {
  if (!result?.citations?.length) return [];
  const uniqueCodes = new Set<string>();
  result.citations.forEach((citation) => {
    const code = (citation.standard_code || "").trim();
    if (code) uniqueCodes.add(code);
  });
  return Array.from(uniqueCodes);
}

export default function App() {
  const auth = useSyncExternalStore(subscribeAuthStore, getAuthSnapshot);

  const [authScreen, setAuthScreen] = useState<"login" | "register" | "chat" | "profile">("login");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authSuccess, setAuthSuccess] = useState("");

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [backendHint, setBackendHint] = useState("正在检测后端连接...");
  const [models, setModels] = useState<ModelOption[]>([]);
  const [selectedModelId, setSelectedModelId] = useState("");
  const [sessionId, setSessionId] = useState(() => getOrCreateSessionId());
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: createMessageId(),
      role: "system",
      content: "你好，我是标准智能助手。你可以直接问标准条款、状态或版本差异。",
    },
  ]);
  const [uploadingText, setUploadingText] = useState(false);
  const [uploadedTextFile, setUploadedTextFile] = useState<UploadTextResponse | null>(null);
  const [uploadStage, setUploadStage] = useState<UploadStage>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadingFileName, setUploadingFileName] = useState("");

  const chatListRef = useRef<HTMLDivElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    void bootstrapAuthSession();
  }, []);

  useEffect(() => {
    void checkBackendHealth();
    void loadModels();
  }, []);

  useEffect(() => {
    if (!auth.initialized) return;
    if (!auth.user) {
      setAuthScreen((prev) => (prev === "register" ? "register" : "login"));
      return;
    }
    setAuthScreen((prev) => (prev === "profile" ? "profile" : "chat"));
  }, [auth.initialized, auth.user]);

  useEffect(() => {
    const list = chatListRef.current;
    if (!list) return;
    list.scrollTop = list.scrollHeight;
  }, [messages, loading]);

  const selectedModel = useMemo(
    () => models.find((model) => model.model_id === selectedModelId) ?? null,
    [models, selectedModelId]
  );

  const latestAssistantWithResult = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message.role === "assistant" && message.result) {
        return message;
      }
    }
    return null;
  }, [messages]);

  const recentQueries = useMemo(
    () =>
      messages
        .filter((message): message is Extract<ChatMessage, { role: "user" }> => message.role === "user")
        .map((message) => message.content)
        .slice(-12)
        .reverse(),
    [messages]
  );

  async function checkBackendHealth() {
    setBackendStatus("checking");
    setBackendHint("正在检测后端连接...");

    try {
      const result = await getHealth();
      setBackendStatus("online");
      setBackendHint(`后端连接正常（status=${result.status}）`);
    } catch (error) {
      setBackendStatus("offline");
      const message =
        error instanceof ApiError
          ? `${error.detail}（HTTP ${error.status}）`
          : error instanceof Error
            ? error.message
            : "未知错误";
      setBackendHint(`后端不可用：${message}`);
    }
  }

  async function loadModels() {
    try {
      const result = await getModels();
      setModels(result.models ?? []);
      setSelectedModelId((previous) => {
        if (previous && result.models?.some((model) => model.model_id === previous)) {
          return previous;
        }
        return result.default_model_id ?? result.models?.[0]?.model_id ?? "";
      });
    } catch (error) {
      const detail =
        error instanceof ApiError
          ? `${error.detail}（HTTP ${error.status}）`
          : error instanceof Error
            ? error.message
            : "未知错误";
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          role: "system",
          content: `模型列表加载失败：${detail}`,
        },
      ]);
    }
  }

  function newSession() {
    const next = createNewSessionId();
    setSessionId(next);
    setUploadedTextFile(null);
    setMessages([
      {
        id: createMessageId(),
        role: "system",
        content: "已创建新会话。你可以继续提问标准问题。",
      },
    ]);
  }

  function clearMessages() {
    setMessages([
      {
        id: createMessageId(),
        role: "system",
        content: "会话内容已清空。你可以继续提问。",
      },
    ]);
  }

  function applyComposerTool(tool: ComposerTool) {
    setInput((prev) => {
      if (!prev.trim()) return tool.seedText;
      return `${prev}\n${tool.seedText}`;
    });
  }

  async function handleTextFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    const fileExt = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (fileExt === "pdf") {
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          role: "system",
          content: "已选择 PDF 文件。当前后端上传接口仍是文本模式，仅支持 txt/md/csv/json；PDF 识别将在 Step 14.1 接入。",
        },
      ]);
      event.target.value = "";
      return;
    }

    setUploadingText(true);
    setUploadStage("uploading");
    setUploadProgress(0);
    setUploadingFileName(file.name);
    try {
      const uploaded = await postUploadTextFile({
        file,
        session_id: sessionId,
        onProgress: (progress) => {
          setUploadProgress(progress);
          if (progress >= 100) {
            setUploadStage("processing");
            return;
          }
          setUploadStage("uploading");
        },
      });
      setUploadedTextFile(uploaded);
      setUploadProgress(100);
      setUploadStage("processing");
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          role: "system",
          content: `文本文件「${uploaded.file_name}」上传成功并已完成 GLM-OCR 识别。摘要：${uploaded.ocr_summary}`,
        },
      ]);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        await handleLogout();
        return;
      }

      const detail =
        error instanceof ApiError
          ? `${error.detail}（HTTP ${error.status}）`
          : error instanceof Error
            ? error.message
            : "未知错误";
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          role: "system",
          content: `文本上传失败：${detail}`,
        },
      ]);
    } finally {
      setUploadingText(false);
      setUploadStage("idle");
      event.target.value = "";
    }
  }

  async function handleLogin(payload: { username: string; password: string }) {
    setAuthLoading(true);
    setAuthError("");
    setAuthSuccess("");
    try {
      await login(payload);
      setAuthScreen("chat");
    } catch (error) {
      const detail =
        error instanceof ApiError
          ? `${error.detail}（HTTP ${error.status}）`
          : error instanceof Error
            ? error.message
            : "未知错误";
      setAuthError(detail);
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleRegister(payload: {
    username: string;
    password: string;
    nickname?: string;
    email?: string;
    phone?: string;
  }) {
    setAuthLoading(true);
    setAuthError("");
    setAuthSuccess("");
    try {
      await register(payload);
      setAuthSuccess("注册成功，请使用新账号登录。");
      setAuthScreen("login");
    } catch (error) {
      const detail =
        error instanceof ApiError
          ? `${error.detail}（HTTP ${error.status}）`
          : error instanceof Error
            ? error.message
            : "未知错误";
      setAuthError(detail);
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleLogout() {
    setAuthLoading(true);
    setAuthError("");
    setAuthSuccess("");
    try {
      await logout();
      setUploadedTextFile(null);
      setMessages([
        {
          id: createMessageId(),
          role: "system",
          content: "你好，我是标准智能助手。你可以直接问标准条款、状态或版本差异。",
        },
      ]);
      setAuthScreen("login");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleUpdateProfile(payload: {
    nickname?: string | null;
    email?: string | null;
    phone?: string | null;
    avatar_url?: string | null;
  }) {
    setAuthLoading(true);
    setAuthError("");
    setAuthSuccess("");
    try {
      await updateMe(payload);
      setAuthSuccess("资料已更新");
    } catch (error) {
      const detail =
        error instanceof ApiError
          ? `${error.detail}（HTTP ${error.status}）`
          : error instanceof Error
            ? error.message
            : "未知错误";
      setAuthError(detail);
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleChangePassword(payload: { old_password: string; new_password: string }) {
    setAuthLoading(true);
    setAuthError("");
    setAuthSuccess("");
    try {
      await changeMyPassword(payload);
      setAuthSuccess("密码已更新");
    } catch (error) {
      const detail =
        error instanceof ApiError
          ? `${error.detail}（HTTP ${error.status}）`
          : error instanceof Error
            ? error.message
            : "未知错误";
      setAuthError(detail);
    } finally {
      setAuthLoading(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = input.trim();
    if (!query || loading) return;

    const assistantMessageId = createMessageId();
    let streamError: string | null = null;

    setLoading(true);
    setInput("");
    setMessages((prev) => [
      ...prev,
      { id: createMessageId(), role: "user", content: query },
      { id: assistantMessageId, role: "assistant", content: "", streaming: true },
    ]);

    try {
      await postChatStream(
        {
          session_id: sessionId,
          query,
          model_id: selectedModelId || undefined,
        },
        (eventPayload) => {
          if (eventPayload.type === "delta") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId && msg.role === "assistant"
                  ? { ...msg, content: `${msg.content}${eventPayload.content}`, streaming: true }
                  : msg
              )
            );
            return;
          }

          if (eventPayload.type === "done") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId && msg.role === "assistant"
                  ? {
                      ...msg,
                      content: eventPayload.answer || msg.content,
                      result: {
                        answer: eventPayload.answer,
                        citations: eventPayload.citations,
                        data: eventPayload.data,
                        action: eventPayload.action,
                        trace_id: eventPayload.trace_id,
                        timestamp: eventPayload.timestamp,
                      },
                      streaming: false,
                    }
                  : msg
              )
            );
            return;
          }

          if (eventPayload.type === "error") {
            streamError = eventPayload.error;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId && msg.role === "assistant"
                  ? {
                      ...msg,
                      content: msg.content || `请求失败：${eventPayload.error}`,
                      streaming: false,
                    }
                  : msg
              )
            );
          }
        }
      );

      if (streamError) {
        setMessages((prev) => [
          ...prev,
          {
            id: createMessageId(),
            role: "system",
            content: `流式调用失败：${streamError}`,
          },
        ]);
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        await handleLogout();
        return;
      }
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          role: "system",
          content:
            error instanceof ApiError
              ? `请求失败：${error.detail}（HTTP ${error.status}）`
              : `请求失败，请稍后重试。${error instanceof Error ? `(${error.message})` : ""}`,
        },
      ]);
    } finally {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId && msg.role === "assistant"
            ? { ...msg, streaming: false }
            : msg
        )
      );
      setLoading(false);
    }
  }

  function handleInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  }

  const latestCitations = latestAssistantWithResult?.result?.citations ?? [];
  const latestResult = latestAssistantWithResult?.result;
  const userMessageCount = messages.filter((message) => message.role === "user").length;
  const assistantMessageCount = messages.filter((message) => message.role === "assistant").length;
  const latestRetrievedCount = readRetrievedCount(latestResult);
  const totalMessages = userMessageCount + assistantMessageCount;
  const welcomeMode = totalMessages === 0;
  const uploadActionDisabled = uploadingText || loading;

  if (!auth.initialized) {
    return (
      <main className="auth-shell">
        <section className="auth-card compact">
          <h1>正在初始化登录状态</h1>
          <p className="auth-sub">请稍候，正在恢复会话...</p>
        </section>
      </main>
    );
  }

  const authFallback =
    authScreen === "register" ? (
      <RegisterPage
        loading={authLoading}
        error={authError}
        onSubmit={handleRegister}
        onSwitchToLogin={() => {
          setAuthError("");
          setAuthSuccess("");
          setAuthScreen("login");
        }}
      />
    ) : (
      <LoginPage
        loading={authLoading}
        error={authError}
        success={authSuccess}
        onSubmit={handleLogin}
        onSwitchToRegister={() => {
          setAuthError("");
          setAuthSuccess("");
          setAuthScreen("register");
        }}
      />
    );

  if (auth.user && authScreen === "profile") {
    return (
      <ProfilePage
        user={auth.user}
        loading={authLoading}
        error={authError}
        success={authSuccess}
        onBack={() => {
          setAuthError("");
          setAuthSuccess("");
          setAuthScreen("chat");
        }}
        onUpdateProfile={handleUpdateProfile}
        onChangePassword={handleChangePassword}
      />
    );
  }

  return (
    <ProtectedRoute isAuthenticated={Boolean(auth.user)} fallback={authFallback}>
    <main className="q-layout">
      <div className="q-top-line" aria-hidden="true" />

      <aside className="q-sidebar">
        <div className="sidebar-head">
          <div className="sidebar-brand">
            <span className="sidebar-brand-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" role="img">
                <path d="M11.6 2.2a2 2 0 0 1 .8 0l3.2.9a2 2 0 0 1 1.2.95l1.7 2.9a2 2 0 0 1 0 2l-1.7 2.9a2 2 0 0 1-1.2.95l-3.2.9a2 2 0 0 1-.8 0l-3.2-.9a2 2 0 0 1-1.2-.95L5.5 11a2 2 0 0 1 0-2l1.7-2.9a2 2 0 0 1 1.2-.95z" />
                <path d="M12 7.4a1 1 0 0 1 .86.48l2.1 3.62a1 1 0 0 1-.87 1.5H9.9a1 1 0 0 1-.87-1.5l2.1-3.62a1 1 0 0 1 .87-.48z" />
              </svg>
            </span>
            <div className="sidebar-logo">标准智能助手</div>
          </div>
          <button type="button" className="icon-ghost" onClick={checkBackendHealth} aria-label="检测后端连接">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 5a7 7 0 1 0 6.5 9.6 1 1 0 1 1 1.88.66A9 9 0 1 1 12 3h.1l-1.45-1.45a1 1 0 1 1 1.42-1.42l3.1 3.1a1 1 0 0 1 0 1.42l-3.1 3.1a1 1 0 1 1-1.42-1.42L12.1 5z" />
            </svg>
          </button>
        </div>

        <div className="sidebar-actions">
          <button type="button" className="new-chat-btn" onClick={newSession}>
            <span className="btn-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path d="M12 4a1 1 0 0 1 1 1v6h6a1 1 0 1 1 0 2h-6v6a1 1 0 1 1-2 0v-6H5a1 1 0 1 1 0-2h6V5a1 1 0 0 1 1-1z" />
              </svg>
            </span>
            <span>新对话</span>
          </button>
          <button
            type="button"
            className="mini-action-btn"
            onClick={clearMessages}
            aria-label="清空对话记录"
            disabled={loading}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6.2 7.7a5.8 5.8 0 0 1 11.4 1.4 5.8 5.8 0 1 1-5.6-7.1 1 1 0 1 1 0 2 3.8 3.8 0 1 0 3.6 4.6 3.8 3.8 0 0 0-7.5-.8 1 1 0 1 1-1.9-.3z" />
            </svg>
          </button>
        </div>

        <section className="sidebar-block">
          <div className="sidebar-subtitle">对话分组</div>
          <div className="sidebar-block-head">
            <h2>最近对话</h2>
            <button type="button" className="icon-ghost small" onClick={clearMessages} aria-label="清空最近对话">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 7a1 1 0 0 1 1-1h14a1 1 0 1 1 0 2H5a1 1 0 0 1-1-1zm3 6a1 1 0 0 1 1-1h8a1 1 0 1 1 0 2H8a1 1 0 0 1-1-1zm-3 6a1 1 0 0 1 1-1h14a1 1 0 1 1 0 2H5a1 1 0 0 1-1-1z" />
              </svg>
            </button>
          </div>
          <div className="history-list">
            {(recentQueries.length ? recentQueries : QUICK_QUESTIONS).map((query, index) => (
              <button
                key={`${query}-${index}`}
                type="button"
                className="history-item"
                onClick={() => setInput(query)}
                disabled={loading}
              >
                {query}
              </button>
            ))}
          </div>
        </section>

        <section className="sidebar-footer">
          <div className="workspace-avatar" aria-hidden="true">
            SA
          </div>
          <div className="workspace-info">
            <p className="workspace-title">{auth.user?.nickname || auth.user?.username || "我的空间"}</p>
            <p className="workspace-meta">
              {statusLabel(backendStatus)} · {selectedModel?.display_name || "未选择"}
            </p>
          </div>
        </section>
      </aside>

      <section className="q-main">
        <header className="main-topbar">
          <div className="model-bar">
            <select
              id="model-select"
              className="model-select"
              value={selectedModelId}
              onChange={(eventPayload) => setSelectedModelId(eventPayload.target.value)}
              disabled={loading || !models.length}
              aria-label="选择问答模型"
            >
              {models.map((model) => (
                <option key={model.model_id} value={model.model_id}>
                  {model.display_name}
                </option>
              ))}
            </select>
          </div>

          <div className="topbar-right">
            <span className="meta-chip">连接 {statusLabel(backendStatus)}</span>
            <span className="meta-chip">检索 {latestRetrievedCount}</span>
            {uploadedTextFile ? <span className="meta-chip">文件 {uploadedTextFile.file_name}</span> : null}
            <label
              htmlFor={uploadActionDisabled ? undefined : "text-file-upload-input"}
              className={`ghost-btn upload-trigger-label${uploadActionDisabled ? " disabled" : ""}`}
              aria-disabled={uploadActionDisabled}
            >
              {uploadingText ? `上传中 ${uploadProgress}%` : "上传文本"}
            </label>
            <button type="button" className="ghost-btn" onClick={() => setAuthScreen("profile")}>
              个人资料
            </button>
            <button type="button" className="ghost-btn" onClick={clearMessages}>
              清空消息
            </button>
            <button type="button" className="ghost-btn" onClick={handleLogout}>
              退出登录
            </button>
          </div>
        </header>

        <div className={`main-content ${welcomeMode ? "welcome-mode" : "chat-mode"}`}>
          {welcomeMode ? (
            <div className="welcome-center">
              <h1>你好，我是标准智能助手</h1>
              <p>你可以提问标准号、标准名称、版本差异、状态与适用范围。</p>

              <form className="welcome-composer" ref={formRef} onSubmit={onSubmit}>
                <label htmlFor="chat-input-text" className="visually-hidden">
                  输入标准问答问题
                </label>
                <textarea
                  id="chat-input-text"
                  value={input}
                  onChange={(eventPayload) => setInput(eventPayload.target.value)}
                  onKeyDown={handleInputKeyDown}
                  placeholder="向标准智能助手提问（支持直接粘贴文本）"
                  disabled={loading}
                  rows={3}
                  aria-label="标准问题输入框"
                />
                {uploadingText ? (
                  <section className="upload-progress-card upload-progress-inline" aria-live="polite">
                    <div className="upload-progress-file-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24">
                        <path d="M6 2a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8.8a2 2 0 0 0-.59-1.41l-4.8-4.8A2 2 0 0 0 13.2 2H6zm7 1.7 5.3 5.3H14a1 1 0 0 1-1-1V3.7zM7 14a1 1 0 0 1 1-1h8a1 1 0 1 1 0 2H8a1 1 0 0 1-1-1zm1 3a1 1 0 1 0 0 2h5a1 1 0 1 0 0-2H8z" />
                      </svg>
                    </div>
                    <div className="upload-progress-body">
                      <div className="upload-progress-name" title={uploadingFileName}>
                        {uploadingFileName || "正在上传文件"}
                      </div>
                      <div className="upload-progress-meta">
                        <span className="upload-progress-spinner" aria-hidden="true" />
                        <span>{uploadStage === "processing" ? "识别中" : "上传中"}</span>
                        <span>{uploadProgress}%</span>
                      </div>
                      <div className="upload-progress-track" aria-hidden="true">
                        <span style={{ width: `${Math.max(uploadProgress, 4)}%` }} />
                      </div>
                    </div>
                  </section>
                ) : null}
                <div className="composer-bottom">
                  <div className="composer-tool-list" role="group" aria-label="快捷模式">
                    {COMPOSER_TOOLS.map((tool) => (
                      <button
                        key={tool.id}
                        type="button"
                        className="composer-tool-chip"
                        disabled={loading}
                        onClick={() => applyComposerTool(tool)}
                      >
                        <span className="composer-tool-icon">{renderComposerToolIcon(tool.id)}</span>
                        <span>{tool.label}</span>
                      </button>
                    ))}
                  </div>
                  <div className="composer-action-group">
                    <button
                      type="button"
                      className="composer-icon-btn"
                      aria-label="联网能力暂未开启"
                      title="联网能力暂未开启"
                      disabled
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M12 2a10 10 0 1 0 10 10A10.01 10.01 0 0 0 12 2zm7.93 9h-3.05a15.48 15.48 0 0 0-1.2-5.04A8.04 8.04 0 0 1 19.93 11zM12 4.06A13.22 13.22 0 0 1 14.82 11H9.18A13.22 13.22 0 0 1 12 4.06zM8.32 5.96A15.48 15.48 0 0 0 7.12 11H4.07a8.04 8.04 0 0 1 4.25-5.04zM4.07 13h3.05a15.48 15.48 0 0 0 1.2 5.04A8.04 8.04 0 0 1 4.07 13zM12 19.94A13.22 13.22 0 0 1 9.18 13h5.64A13.22 13.22 0 0 1 12 19.94zm3.68-1.9A15.48 15.48 0 0 0 16.88 13h3.05a8.04 8.04 0 0 1-4.25 5.04z" />
                      </svg>
                    </button>
                    <label
                      htmlFor={uploadActionDisabled ? undefined : "text-file-upload-input"}
                      className={`composer-icon-btn upload-trigger-label${uploadActionDisabled ? " disabled" : ""}`}
                      aria-label="上传文本文件"
                      aria-disabled={uploadActionDisabled}
                      title="上传文本文件"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M16.5 6a3.5 3.5 0 0 1 0 7H8a1 1 0 1 1 0-2h8.5a1.5 1.5 0 0 0 0-3H7a3.5 3.5 0 0 0 0 7h7.5a1 1 0 1 1 0 2H7a5.5 5.5 0 0 1 0-11h9.5z" />
                      </svg>
                    </label>
                    <button type="submit" className="composer-send-btn" disabled={loading || !input.trim()}>
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M12 4a1 1 0 0 1 1 1v9.59l3.3-3.3a1 1 0 1 1 1.4 1.42l-5 5a1 1 0 0 1-1.4 0l-5-5a1 1 0 1 1 1.4-1.42l3.3 3.3V5a1 1 0 0 1 1-1z" />
                      </svg>
                    </button>
                  </div>
                </div>
              </form>
            </div>
          ) : (
            <>
              <div className="chat-list" ref={chatListRef} role="log" aria-live="polite" aria-relevant="additions text">
                {messages.map((message) => {
                  const citationCodes =
                    message.role === "assistant" && message.result
                      ? readCitationCodes(message.result)
                      : [];

                  return (
                    <article
                      key={message.id}
                      className={`msg ${message.role}${message.role === "assistant" && message.streaming ? " streaming" : ""}`}
                    >
                    {message.role !== "system" ? (
                      <div className="msg-head">
                        <span className="msg-title">
                          {messageTitle(message, selectedModel?.display_name || "标准智能助手")}
                        </span>
                        {message.role === "assistant" && message.result?.timestamp ? (
                          <time className="msg-time">{formatTimestamp(message.result.timestamp)}</time>
                        ) : null}
                        {message.role === "assistant" && message.streaming ? (
                          <span className="stream-badge">生成中</span>
                        ) : null}
                      </div>
                    ) : null}

                    <div
                      className={`msg-content ${
                        message.role === "assistant" ? "markdown-content" : "plain-content"
                      }`}
                    >
                      {message.role === "assistant" ? (
                        <MarkdownContent
                          markdown={message.content || (message.streaming ? "正在生成回答，请稍候..." : "")}
                        />
                      ) : (
                        message.content
                      )}
                      {message.role === "assistant" && message.streaming ? (
                        <span className="stream-caret" aria-hidden="true">
                          ▋
                        </span>
                      ) : null}
                    </div>

                    {message.role === "assistant" && citationCodes.length ? (
                      <div className="citation-strip">
                        <div className="citation-strip-title">其他相关标准</div>
                        <div className="citation-codes">
                          {citationCodes.map((code) => (
                            <span key={`${message.id}-${code}`} className="citation-code-chip">
                              {code}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}
                    </article>
                  );
                })}
              </div>

              <form className="chat-input-docked" ref={formRef} onSubmit={onSubmit}>
                <label htmlFor="chat-input-docked" className="visually-hidden">
                  输入标准问答问题
                </label>
                <textarea
                  id="chat-input-docked"
                  value={input}
                  onChange={(eventPayload) => setInput(eventPayload.target.value)}
                  onKeyDown={handleInputKeyDown}
                  placeholder="向标准智能助手提问（支持直接粘贴文本）"
                  disabled={loading}
                  rows={3}
                  aria-label="标准问题输入框"
                />
                {uploadingText ? (
                  <section className="upload-progress-card upload-progress-inline" aria-live="polite">
                    <div className="upload-progress-file-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24">
                        <path d="M6 2a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8.8a2 2 0 0 0-.59-1.41l-4.8-4.8A2 2 0 0 0 13.2 2H6zm7 1.7 5.3 5.3H14a1 1 0 0 1-1-1V3.7zM7 14a1 1 0 0 1 1-1h8a1 1 0 1 1 0 2H8a1 1 0 0 1-1-1zm1 3a1 1 0 1 0 0 2h5a1 1 0 1 0 0-2H8z" />
                      </svg>
                    </div>
                    <div className="upload-progress-body">
                      <div className="upload-progress-name" title={uploadingFileName}>
                        {uploadingFileName || "正在上传文件"}
                      </div>
                      <div className="upload-progress-meta">
                        <span className="upload-progress-spinner" aria-hidden="true" />
                        <span>{uploadStage === "processing" ? "识别中" : "上传中"}</span>
                        <span>{uploadProgress}%</span>
                      </div>
                      <div className="upload-progress-track" aria-hidden="true">
                        <span style={{ width: `${Math.max(uploadProgress, 4)}%` }} />
                      </div>
                    </div>
                  </section>
                ) : null}
                <div className="composer-bottom">
                  <div className="composer-tool-list" role="group" aria-label="快捷模式">
                    {COMPOSER_TOOLS.map((tool) => (
                      <button
                        key={`chat-${tool.id}`}
                        type="button"
                        className="composer-tool-chip"
                        disabled={loading}
                        onClick={() => applyComposerTool(tool)}
                      >
                        <span className="composer-tool-icon">{renderComposerToolIcon(tool.id)}</span>
                        <span>{tool.label}</span>
                      </button>
                    ))}
                  </div>
                  <div className="composer-action-group">
                    <button
                      type="button"
                      className="composer-icon-btn"
                      aria-label="联网能力暂未开启"
                      title="联网能力暂未开启"
                      disabled
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M12 2a10 10 0 1 0 10 10A10.01 10.01 0 0 0 12 2zm7.93 9h-3.05a15.48 15.48 0 0 0-1.2-5.04A8.04 8.04 0 0 1 19.93 11zM12 4.06A13.22 13.22 0 0 1 14.82 11H9.18A13.22 13.22 0 0 1 12 4.06zM8.32 5.96A15.48 15.48 0 0 0 7.12 11H4.07a8.04 8.04 0 0 1 4.25-5.04zM4.07 13h3.05a15.48 15.48 0 0 0 1.2 5.04A8.04 8.04 0 0 1 4.07 13zM12 19.94A13.22 13.22 0 0 1 9.18 13h5.64A13.22 13.22 0 0 1 12 19.94zm3.68-1.9A15.48 15.48 0 0 0 16.88 13h3.05a8.04 8.04 0 0 1-4.25 5.04z" />
                      </svg>
                    </button>
                    <label
                      htmlFor={uploadActionDisabled ? undefined : "text-file-upload-input"}
                      className={`composer-icon-btn upload-trigger-label${uploadActionDisabled ? " disabled" : ""}`}
                      aria-label="上传文本文件"
                      aria-disabled={uploadActionDisabled}
                      title="上传文本文件"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M16.5 6a3.5 3.5 0 0 1 0 7H8a1 1 0 1 1 0-2h8.5a1.5 1.5 0 0 0 0-3H7a3.5 3.5 0 0 0 0 7h7.5a1 1 0 1 1 0 2H7a5.5 5.5 0 0 1 0-11h9.5z" />
                      </svg>
                    </label>
                    <button type="submit" className="composer-send-btn" disabled={loading || !input.trim()}>
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M12 4a1 1 0 0 1 1 1v9.59l3.3-3.3a1 1 0 1 1 1.4 1.42l-5 5a1 1 0 0 1-1.4 0l-5-5a1 1 0 1 1 1.4-1.42l3.3 3.3V5a1 1 0 0 1 1-1z" />
                      </svg>
                    </button>
                  </div>
                </div>
              </form>
            </>
          )}
        </div>

        <footer className="main-footer">
          <span>引用条数：{latestCitations.length}</span>
          <span>消息数：{totalMessages}</span>
          <span>文件识别：{uploadedTextFile ? "已完成" : "未上传"}</span>
          <span>后端提示：{backendHint}</span>
        </footer>
      </section>
      <input
        id="text-file-upload-input"
        ref={fileInputRef}
        type="file"
        accept=".txt,.md,.csv,.json,.pdf,text/plain,application/json,text/csv,application/pdf"
        onChange={handleTextFileChange}
        className="visually-hidden"
        tabIndex={-1}
      />
    </main>
    </ProtectedRoute>
  );
}
