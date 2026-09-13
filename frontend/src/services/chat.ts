import type {
  ApiCitation,
  Citation,
  Message,
  ModelOption,
  Thread,
  ThinkingLevel,
} from "@/types/chat"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

export function mapCitation({
  parent_id,
  document_id,
  content,
  filename,
  source,
  page_start,
  page_end,
  score,
  score_type,
  hit_count,
  matched_child_ids,
}: ApiCitation): Citation {
  return {
    parentId: parent_id,
    documentId: document_id,
    content,
    filename,
    source,
    pageStart: page_start,
    pageEnd: page_end,
    score,
    scoreType: score_type,
    hitCount: hit_count,
    matchedChildIds: matched_child_ids,
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init)

  if (!response.ok) {
    throw new Error("请求失败，请检查后端服务和 SQLite 配置。")
  }

  return response.json() as Promise<T>
}

export async function listThreads(): Promise<Thread[]> {
  return request<Thread[]>("/api/threads")
}

export async function listModels(): Promise<ModelOption[]> {
  const models = await request<
    Array<{
      id: string
      label: string
      context_window_tokens: number
      thinking_levels: ThinkingLevel[]
    }>
  >("/api/models")

  return models.map(({ context_window_tokens, thinking_levels, ...model }) => ({
    ...model,
    contextWindowTokens: context_window_tokens,
    thinkingLevels: thinking_levels,
  }))
}

export async function getThreadMessages(threadId: string): Promise<Message[]> {
  const messages = await request<
    Array<
      Omit<Message, "references" | "reasoningContent" | "thinkingDurationMs"> & {
        reasoning_content?: string
        thinking_duration_ms?: number
        references?: ApiCitation[]
      }
    >
  >(`/api/threads/${encodeURIComponent(threadId)}/messages`)

  return messages.map(({ reasoning_content, thinking_duration_ms, references, ...message }) => ({
    ...message,
    reasoningContent: reasoning_content ?? "",
    thinkingDurationMs: thinking_duration_ms ?? 0,
    references: (references ?? []).map(mapCitation),
  }))
}

export async function deleteThread(threadId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/threads/${encodeURIComponent(threadId)}`,
    { method: "DELETE" },
  )

  if (!response.ok) {
    throw new Error("删除会话失败，请检查后端服务。")
  }
}
