export type ActionType = "continue" | "clarify";

export interface ChatRequest {
  session_id: string;
  query: string;
  model_id?: string;
}

export interface Citation {
  standard_code: string;
  version: string;
  clause: string;
  scope: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  data: Record<string, unknown>;
  action: ActionType;
  trace_id: string;
  timestamp: string;
}

export interface StreamMetaEvent {
  type: "meta";
  trace_id: string;
  timestamp: string;
  requested_model_id?: string | null;
}

export interface StreamDeltaEvent {
  type: "delta";
  content: string;
}

export interface StreamDoneEvent extends ChatResponse {
  type: "done";
}

export interface StreamErrorEvent {
  type: "error";
  status: number;
  error: string;
  trace_id?: string;
}

export type ChatStreamEvent =
  | StreamMetaEvent
  | StreamDeltaEvent
  | StreamDoneEvent
  | StreamErrorEvent;

export interface ModelOption {
  model_id: string;
  display_name: string;
  provider: string;
  model_name: string;
}

export interface ModelListResponse {
  default_model_id: string;
  models: ModelOption[];
}
