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

export function buildUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export async function parseError(response: Response): Promise<never> {
  const fallback = `请求失败: ${response.status}`;
  let detail = fallback;

  try {
    const body = (await response.json()) as { detail?: string | Array<Record<string, unknown>> };
    if (typeof body.detail === "string" && body.detail.trim()) {
      detail = body.detail;
    } else if (Array.isArray(body.detail) && body.detail.length > 0) {
      const messages = body.detail.map((item) => {
        const locRaw = Array.isArray(item.loc) ? item.loc.join(".") : "body";
        const msgRaw = typeof item.msg === "string" ? item.msg : "参数校验失败";
        return `${locRaw}: ${msgRaw}`;
      });
      detail = messages.join("；");
    }
  } catch {
    // Ignore parse errors and keep fallback detail.
  }

  throw new ApiError(response.status, detail);
}
