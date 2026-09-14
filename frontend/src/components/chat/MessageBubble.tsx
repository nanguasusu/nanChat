import { useState } from "react"
import { Bot, FileText, UserRound } from "lucide-react"

import { AgenticProcess } from "@/components/chat/AgenticProcess"
import { Markdown } from "@/components/prompt-kit/markdown"
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/prompt-kit/reasoning"
import { ThinkingBar } from "@/components/prompt-kit/thinking-bar"
import type { Citation, Message } from "@/types/chat"
import { cn } from "@/lib/utils"

function formatThinkingDuration(durationMs?: number) {
  if (durationMs === undefined) return null

  return `${Math.max(1, Math.round(durationMs / 1000))} 秒`
}

interface MessageBubbleProps {
  message: Message
  onCitationClick: (citation: Citation) => void
}

function formatCitationPages(citation: Citation) {
  if (citation.pageStart === null) return "无页码"
  if (citation.pageStart === citation.pageEnd) return `第 ${citation.pageStart} 页`
  return `第 ${citation.pageStart}-${citation.pageEnd} 页`
}

export function MessageBubble({ message, onCitationClick }: MessageBubbleProps) {
  const isUser = message.role === "user"
  const isStreaming = message.status === "streaming"
  const isThinking = isStreaming && message.streamPhase === "thinking"
  const isAgentic = message.ragMode === "agentic" || Boolean(message.agenticStages?.length)
  const hasReasoning =
    !isAgentic &&
    (isThinking ||
    Boolean(message.reasoningContent) ||
    (message.thinkingDurationMs !== undefined && message.thinkingDurationMs > 0))
  const thinkingDuration = formatThinkingDuration(message.thinkingDurationMs)
  const [isReasoningOpen, setIsReasoningOpen] = useState(false)

  return (
    <div className={cn("flex gap-2 sm:gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="mt-0.5 hidden h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-background text-foreground sm:flex">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div
        className={cn(
          "min-w-0 overflow-x-auto text-sm leading-6",
          isUser
            ? "max-w-[min(42rem,92%)] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-foreground px-3.5 py-2.5 text-background sm:max-w-[min(42rem,85%)] sm:px-4 sm:py-3"
            : "max-w-full text-foreground sm:max-w-[min(48rem,90%)]",
        )}
      >
        {!isUser && message.agenticStages && message.agenticStages.length > 0 && (
          <AgenticProcess events={message.agenticStages} isStreaming={isStreaming} />
        )}
        {!isUser && hasReasoning && (
          <Reasoning
            className="mb-3"
            isStreaming={isThinking}
            onOpenChange={setIsReasoningOpen}
            open={isReasoningOpen}
          >
            {isThinking ? (
              <ThinkingBar
                onClick={() => setIsReasoningOpen((value) => !value)}
                text="思考中"
              />
            ) : (
              <ReasoningTrigger className="text-sm text-muted-foreground hover:text-foreground">
                {thinkingDuration ? `已思考（用时 ${thinkingDuration}）` : "已思考"}
              </ReasoningTrigger>
            )}
            <ReasoningContent
              contentClassName="scrollbar-hidden max-h-64 overflow-y-auto pr-2"
              markdown
            >
              {message.reasoningContent || "正在思考..."}
            </ReasoningContent>
          </Reasoning>
        )}
        {!isUser && message.content ? (
          <Markdown
            className="prose prose-sm max-w-none break-words dark:prose-invert [&_img]:max-w-full [&_pre]:overflow-x-auto [&_table]:block [&_table]:max-w-full [&_table]:overflow-x-auto"
            id={message.id}
          >
            {message.content}
          </Markdown>
        ) : (
          message.content
        )}
        {!isUser && message.references && message.references.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-xs text-muted-foreground">引用来源</span>
            {message.references.map((citation) => (
              <button
                aria-label={`查看 ${citation.filename} ${formatCitationPages(citation)}`}
                className="inline-flex max-w-full items-center gap-1.5 rounded-md border border-border bg-muted/40 px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                key={citation.parentId}
                onClick={() => onCitationClick(citation)}
                title={`${citation.filename} · ${formatCitationPages(citation)}`}
                type="button"
              >
                <FileText className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{citation.filename}</span>
                <span className="shrink-0">· {formatCitationPages(citation)}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      {isUser && (
        <div className="mt-0.5 hidden h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground sm:flex">
          <UserRound className="h-4 w-4" />
        </div>
      )}
    </div>
  )
}
