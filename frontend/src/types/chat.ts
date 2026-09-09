export type MessageStatus = "streaming" | "completed" | "error" | "aborted"
export type MessageStreamPhase = "thinking" | "answering"

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  reasoningContent?: string
  thinkingDurationMs?: number
  streamPhase?: MessageStreamPhase
  status?: MessageStatus
}

export interface Thread {
  id: string
  title: string
  created_at: string
  updated_at: string
}
