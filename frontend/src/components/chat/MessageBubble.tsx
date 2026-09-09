import { useState } from "react"
import { Bot, UserRound } from "lucide-react"

import { Markdown } from "@/components/prompt-kit/markdown"
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/prompt-kit/reasoning"
import { ThinkingBar } from "@/components/prompt-kit/thinking-bar"
import type { Message } from "@/types/chat"
import { cn } from "@/lib/utils"

function formatThinkingDuration(durationMs?: number) {
  if (durationMs === undefined) return null

  return `${Math.max(1, Math.round(durationMs / 1000))} 秒`
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user"
  const isStreaming = message.status === "streaming"
  const isThinking = isStreaming && message.streamPhase === "thinking"
  const hasReasoning =
    isThinking ||
    Boolean(message.reasoningContent) ||
    (message.thinkingDurationMs !== undefined && message.thinkingDurationMs > 0)
  const thinkingDuration = formatThinkingDuration(message.thinkingDurationMs)
  const [isReasoningOpen, setIsReasoningOpen] = useState(false)

  return (
    <div className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-background text-foreground">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div
        className={cn(
          "min-w-0 text-sm leading-6",
          isUser
            ? "max-w-[min(42rem,85%)] whitespace-pre-wrap rounded-2xl rounded-br-md bg-foreground px-4 py-3 text-background"
            : "max-w-[min(48rem,90%)] text-foreground",
        )}
      >
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
            className="prose prose-sm max-w-none dark:prose-invert"
            id={message.id}
          >
            {message.content}
          </Markdown>
        ) : (
          message.content
        )}
      </div>
      {isUser && (
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <UserRound className="h-4 w-4" />
        </div>
      )}
    </div>
  )
}
