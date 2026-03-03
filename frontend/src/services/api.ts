import type {
  ChatRequest,
  ChatResponse,
  ChatStreamEvent,
  ModelListResponse,
} from "../types/chat";
import { authJsonFetch } from "./auth";
import { buildUrl, parseError } from "./http";

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

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(buildUrl("/api/v1/health"));
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as { status: string };
}

export async function getModels(): Promise<ModelListResponse> {
  const response = await fetch(buildUrl("/api/v1/models"));
  if (!response.ok) {
    await parseError(response);
  }
  return (await response.json()) as ModelListResponse;
}

export async function postChat(payload: ChatRequest): Promise<ChatResponse> {
  const response = await authJsonFetch("/api/v1/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  return (await response.json()) as ChatResponse;
}

export async function postChatStream(
  payload: ChatRequest,
  onEvent: (event: ChatStreamEvent) => void
): Promise<void> {
  const response = await authJsonFetch("/api/v1/chat/stream", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (!response.body) {
    throw new Error("流式响应为空");
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
