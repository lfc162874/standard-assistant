import type { ChatRequest, ChatResponse, ChatStreamEvent } from "../types/chat";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.name = "ApiError";
  }
}

function buildUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function parseError(response: Response): Promise<never> {
  const fallback = `请求失败: ${response.status}`;
  let detail = fallback;

  try {
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string" && body.detail.trim()) {
      detail = body.detail;
    }
  } catch {
    // Ignore parse errors and keep fallback detail.
  }

  throw new ApiError(response.status, detail);
}

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(buildUrl("/api/v1/health"));
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as { status: string };
}

export async function postChat(payload: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(buildUrl("/api/v1/chat"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    await parseError(response);
  }

  return (await response.json()) as ChatResponse;
}

function parseSseBlock(block: string): ChatStreamEvent | null {
  const lines = block
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const dataLines = lines
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.replace(/^data:\s?/, ""));

  if (!dataLines.length) return null;

  const jsonPayload = dataLines.join("");
  return JSON.parse(jsonPayload) as ChatStreamEvent;
}

export async function postChatStream(
  payload: ChatRequest,
  onEvent: (event: ChatStreamEvent) => void
): Promise<void> {
  const response = await fetch(buildUrl("/api/v1/chat/stream"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    await parseError(response);
  }

  if (!response.body) {
    throw new ApiError(500, "流式响应为空");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      buffer += decoder.decode();
    } else if (value) {
      buffer += decoder.decode(value, { stream: true });
    }

    let delimiterIndex = buffer.indexOf("\n\n");
    while (delimiterIndex !== -1) {
      const block = buffer.slice(0, delimiterIndex).trim();
      buffer = buffer.slice(delimiterIndex + 2);

      if (block) {
        const event = parseSseBlock(block);
        if (event) onEvent(event);
      }

      delimiterIndex = buffer.indexOf("\n\n");
    }

    if (done) break;
  }
}
