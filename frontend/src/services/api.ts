import type {
  ChatRequest,
  ChatResponse,
  ChatStreamEvent,
  ModelListResponse,
  UploadTextResponse,
} from "../types/chat";
import { getAuthSnapshot } from "../store/authStore";
import { authJsonFetch, refreshAuthToken } from "./auth";
import { ApiError, buildUrl, parseError } from "./http";

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

export async function postUploadTextFile(payload: {
  file: File;
  session_id?: string;
  onProgress?: (progress: number) => void;
}): Promise<UploadTextResponse> {
  const formData = new FormData();
  formData.append("file", payload.file);
  if (payload.session_id) {
    formData.append("session_id", payload.session_id);
  }

  const firstToken = await ensureAccessToken();

  try {
    return await uploadTextFileWithProgress(formData, firstToken, payload.onProgress);
  } catch (error) {
    // 上传接口也复用一次刷新令牌逻辑，避免 token 过期时直接失败。
    if (error instanceof ApiError && error.status === 401) {
      const refreshed = await refreshAuthToken();
      if (!refreshed) {
        throw new ApiError(401, "登录已过期，请重新登录");
      }
      const nextToken = getAuthSnapshot().accessToken;
      if (!nextToken) {
        throw new ApiError(401, "登录已过期，请重新登录");
      }
      return uploadTextFileWithProgress(formData, nextToken, payload.onProgress);
    }
    throw error;
  }
}

async function ensureAccessToken(): Promise<string> {
  const token = getAuthSnapshot().accessToken;
  if (token) return token;

  const refreshed = await refreshAuthToken();
  if (!refreshed) {
    throw new ApiError(401, "登录已过期，请重新登录");
  }

  const nextToken = getAuthSnapshot().accessToken;
  if (!nextToken) {
    throw new ApiError(401, "登录已过期，请重新登录");
  }

  return nextToken;
}

function parseApiErrorDetail(status: number, responseText: string): string {
  const fallback = `请求失败: ${status}`;
  if (!responseText.trim()) return fallback;

  try {
    const body = JSON.parse(responseText) as { detail?: string | Array<Record<string, unknown>> };
    if (typeof body.detail === "string" && body.detail.trim()) {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      const messages = body.detail.map((item) => {
        const locRaw = Array.isArray(item.loc) ? item.loc.join(".") : "body";
        const msgRaw = typeof item.msg === "string" ? item.msg : "参数校验失败";
        return `${locRaw}: ${msgRaw}`;
      });
      return messages.join("；");
    }
  } catch {
    // Ignore parse error and fallback to plain message below.
  }

  return responseText.trim() || fallback;
}

function parseUploadJson(xhr: XMLHttpRequest): UploadTextResponse {
  if (xhr.response && typeof xhr.response === "object") {
    return xhr.response as UploadTextResponse;
  }

  const text = (xhr.responseText || "").trim();
  if (!text) {
    throw new ApiError(xhr.status || 500, "上传接口返回为空");
  }

  try {
    return JSON.parse(text) as UploadTextResponse;
  } catch {
    throw new ApiError(xhr.status || 500, "上传接口返回了非 JSON 数据");
  }
}

function uploadTextFileWithProgress(
  formData: FormData,
  accessToken: string,
  onProgress?: (progress: number) => void
): Promise<UploadTextResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", buildUrl("/api/v1/files/upload-text"));
    xhr.responseType = "json";
    xhr.setRequestHeader("Authorization", `Bearer ${accessToken}`);

    xhr.upload.onprogress = (event) => {
      if (!onProgress) return;
      if (event.lengthComputable && event.total > 0) {
        const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
        onProgress(percent);
        return;
      }
      // 部分浏览器拿不到总大小时，给一个保守进度，避免“没反应”的感知。
      onProgress(5);
    };

    xhr.onload = () => {
      const status = xhr.status;
      if (status >= 200 && status < 300) {
        try {
          onProgress?.(100);
          resolve(parseUploadJson(xhr));
        } catch (error) {
          reject(error);
        }
        return;
      }

      const detail = parseApiErrorDetail(status, xhr.responseText || "");
      reject(new ApiError(status || 500, detail));
    };

    xhr.onerror = () => {
      reject(new ApiError(0, "网络异常，上传失败"));
    };

    xhr.onabort = () => {
      reject(new ApiError(499, "上传已取消"));
    };

    xhr.send(formData);
  });
}
