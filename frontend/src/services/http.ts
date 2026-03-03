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
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string" && body.detail.trim()) {
      detail = body.detail;
    }
  } catch {
    // Ignore parse errors and keep fallback detail.
  }

  throw new ApiError(response.status, detail);
}
