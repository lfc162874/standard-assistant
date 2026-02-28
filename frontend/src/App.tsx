import { FormEvent, useEffect, useState } from "react";

import MarkdownContent from "./components/MarkdownContent";
import { ApiError, getHealth, postChatStream } from "./services/api";
import type { ChatResponse } from "./types/chat";
import "./styles.css";

type ChatMessage =
  | { id: string; role: "user"; content: string }
  | { id: string; role: "assistant"; content: string; result?: ChatResponse; streaming?: boolean }
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

function roleLabel(role: ChatMessage["role"]): string {
  if (role === "user") return "用户";
  if (role === "assistant") return "助手";
  return "系统";
}

export default function App() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [backendHint, setBackendHint] = useState("正在检测后端连接...");
  const [sessionId, setSessionId] = useState(() => getOrCreateSessionId());
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: createMessageId(),
      role: "system",
      content: "你好，我是标准智能助手。你可以直接问标准条款、状态或版本差异。",
    },
  ]);

  useEffect(() => {
    void checkBackendHealth();
  }, []);

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
        },
        (event) => {
          if (event.type === "delta") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId && msg.role === "assistant"
                  ? { ...msg, content: `${msg.content}${event.content}`, streaming: true }
                  : msg
              )
            );
            return;
          }

          if (event.type === "done") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId && msg.role === "assistant"
                  ? {
                      ...msg,
                      content: event.answer || msg.content,
                      result: {
                        answer: event.answer,
                        citations: event.citations,
                        data: event.data,
                        action: event.action,
                        trace_id: event.trace_id,
                        timestamp: event.timestamp,
                      },
                      streaming: false,
                    }
                  : msg
              )
            );
            return;
          }

          if (event.type === "error") {
            streamError = event.error;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId && msg.role === "assistant"
                  ? {
                      ...msg,
                      content: msg.content || `请求失败：${event.error}`,
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
              : `请求失败，请稍后重试。${
                  error instanceof Error ? `(${error.message})` : ""
                }`,
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

  return (
    <main className="page">
      <section className="chat-panel">
        <header className="chat-header">
          <div>
            <h1>标准智能助手</h1>
            <p>Web 单页问答版（MVP）</p>
          </div>
          <div className="header-actions">
            <button type="button" className="ghost-btn" onClick={checkBackendHealth}>
              检测连接
            </button>
            <button type="button" className="ghost-btn" onClick={newSession}>
              新会话
            </button>
            <button type="button" className="ghost-btn" onClick={clearMessages}>
              清空消息
            </button>
          </div>
        </header>
        <div className="status-bar">
          <span className={`status-dot ${backendStatus}`} />
          <span>{backendHint}</span>
        </div>
        <div className="session-line">
          <span>user_id: {USER_ID}</span>
          <span>session_id: {sessionId}</span>
        </div>

        <div className="quick-questions">
          {QUICK_QUESTIONS.map((question) => (
            <button
              key={question}
              type="button"
              className="quick-btn"
              disabled={loading}
              onClick={() => setInput(question)}
            >
              {question}
            </button>
          ))}
        </div>

        <div className="chat-list">
          {messages.map((message) => (
            <article
              key={message.id}
              className={`msg ${message.role}${message.role === "assistant" && message.streaming ? " streaming" : ""}`}
            >
              <div className="msg-role">
                {roleLabel(message.role)}
                {message.role === "assistant" && message.streaming ? "（生成中）" : ""}
              </div>
              <div
                className={`msg-content ${
                  message.role === "assistant" ? "markdown-content" : "plain-content"
                }`}
              >
                {message.role === "assistant" ? (
                  <MarkdownContent markdown={message.content || (message.streaming ? "..." : "")} />
                ) : (
                  message.content
                )}
              </div>

              {message.role === "assistant" && message.result ? (
                <div className="msg-meta">
                  <span>trace_id: {message.result.trace_id}</span>
                  <span>action: {message.result.action}</span>
                  <span>time: {formatTimestamp(message.result.timestamp)}</span>
                </div>
              ) : null}

              {message.role === "assistant" && message.result?.citations?.length ? (
                <ul className="citation-list">
                  {message.result.citations.map((citation, index) => (
                    <li key={`${citation.standard_code}-${index}`}>
                      {citation.standard_code} {citation.version} · 条款 {citation.clause}
                    </li>
                  ))}
                </ul>
              ) : null}
            </article>
          ))}
        </div>

        <form className="chat-input" onSubmit={onSubmit}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="请输入你的标准问题，例如：GB/T 19001 最新版变化是什么？"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            {loading ? "发送中..." : "发送"}
          </button>
        </form>
      </section>
    </main>
  );
}
