export type MessageStatus = "streaming" | "completed" | "error" | "aborted"
export type MessageStreamPhase = "thinking" | "answering"
export type ThinkingLevel = "off" | "low" | "medium" | "high" | "xhigh"

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

export interface ModelOption {
  id: string
  label: string
  contextWindowTokens: number
  thinkingLevels: ThinkingLevel[]
}

export interface ContextUsage {
  usedTokens: number
  maxTokens: number
  percent: number
  remainingTokens: number
  estimated: boolean
}

export const DEFAULT_MODEL: ModelOption = {
  id: "LongCat-2.0",
  label: "LongCat 2.0",
  contextWindowTokens: 1_048_576,
  thinkingLevels: ["off", "low", "medium", "high", "xhigh"],
}
