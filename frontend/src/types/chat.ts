export type MessageStatus = "streaming" | "completed" | "error" | "aborted"
export type MessageStreamPhase = "thinking" | "answering"
export type ThinkingLevel = "off" | "low" | "medium" | "high" | "xhigh"
export type CitationScoreType = "rrf" | "reranker"
export type RagMode = "standard" | "agentic"
export type AgenticStage = "initial_retrieval" | "planning" | "task" | "synthesis"
export type AgenticStageStatus = "start" | "done" | "retry"

export interface AgenticStageEvent {
  type: "agentic_stage"
  stage: AgenticStage
  status: AgenticStageStatus
  taskId?: string
  label?: string
  taskCount?: number
  parentCount?: number
  attempts?: number
  resultStatus?: "complete" | "partial" | "no_data" | "error"
}

export interface Citation {
  parentId: string
  documentId: string
  content: string
  filename: string
  source: string
  pageStart: number | null
  pageEnd: number | null
  score: number
  scoreType: CitationScoreType
  hitCount: number
  matchedChildIds: string[]
}

export interface ApiCitation {
  parent_id: string
  document_id: string
  content: string
  filename: string
  source: string
  page_start: number | null
  page_end: number | null
  score: number
  score_type: CitationScoreType
  hit_count: number
  matched_child_ids: string[]
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  reasoningContent?: string
  thinkingDurationMs?: number
  streamPhase?: MessageStreamPhase
  status?: MessageStatus
  ragMode?: RagMode
  agenticStages?: AgenticStageEvent[]
  references?: Citation[]
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
  id: "glm-5.3-flash",
  label: "GLM-5.3 Flash",
  contextWindowTokens: 1_048_576,
  thinkingLevels: ["off", "low", "medium", "high", "xhigh"],
}
