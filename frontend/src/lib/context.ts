import type { ContextUsage, Message } from "@/types/chat"

function estimateTextTokens(text: string) {
  let tokens = 0

  for (const character of text) {
    tokens += /[\u3400-\u9fff]/u.test(character) ? 1 : 0.25
  }

  return tokens
}

export function estimateContextUsage(
  messages: Message[],
  draft: string,
  maxTokens: number,
): ContextUsage {
  const messageTokens = messages.reduce(
    (total, message) => total + estimateTextTokens(`${message.role}: ${message.content}`),
    0,
  )
  const usedTokens = Math.ceil(messageTokens + estimateTextTokens(draft))
  const percent = Math.min(100, Math.round((usedTokens / maxTokens) * 100))

  return {
    usedTokens,
    maxTokens,
    percent,
    remainingTokens: Math.max(0, maxTokens - usedTokens),
    estimated: true,
  }
}

export function formatTokenCount(tokens: number) {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`
  if (tokens >= 1_000) return `${Math.round(tokens / 1_000)}k`
  return `${tokens}`
}
