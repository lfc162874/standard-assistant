import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";

import MarkdownContent from "./components/MarkdownContent";
import { ApiError, getHealth, getModels, postChatStream } from "./services/api";
import type { ChatResponse, ModelOption } from "./types/chat";
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

const USER_ID = "demo_user";
const SESSION_KEY = "standard_assistant_session_id";

type BackendStatus = "checking" | "online" | "offline";

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

  const chatListRef = useRef<HTMLDivElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);

  useEffect(() => {
    void checkBackendHealth();
    void loadModels();
  }, []);

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
          user_id: USER_ID,
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

  return (
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
            <p className="workspace-title">我的空间</p>
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
            <button type="button" className="ghost-btn" onClick={clearMessages}>
              清空消息
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
                  placeholder="向标准智能助手提问"
                  disabled={loading}
                  rows={3}
                  aria-label="标准问题输入框"
                />
                <div className="welcome-tools">
                  <div className="welcome-quick-tags">
                    {QUICK_QUESTIONS.map((question) => (
                      <button
                        key={question}
                        type="button"
                        className="quick-tag"
                        disabled={loading}
                        onClick={() => setInput(question)}
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                  <button type="submit" className="send-btn" disabled={loading || !input.trim()}>
                    {loading ? "发送中" : "发送"}
                  </button>
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
                  placeholder="继续提问标准问题..."
                  disabled={loading}
                  rows={3}
                  aria-label="标准问题输入框"
                />
                <div className="chat-input-footer">
                  <span className="input-tip">Enter 发送，Shift+Enter 换行</span>
                  <button type="submit" className="send-btn" disabled={loading || !input.trim()}>
                    {loading ? "发送中" : "发送"}
                  </button>
                </div>
              </form>
            </>
          )}
        </div>

        <footer className="main-footer">
          <span>引用条数：{latestCitations.length}</span>
          <span>消息数：{totalMessages}</span>
          <span>后端提示：{backendHint}</span>
        </footer>
      </section>
    </main>
  );
}
