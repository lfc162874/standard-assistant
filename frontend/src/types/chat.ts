export type ActionType = "continue" | "clarify";

export interface ChatRequest {
  user_id: string;
  session_id: string;
  query: string;
}

export interface Citation {
  standard_code: string;
  version: string;
  clause: string;
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
