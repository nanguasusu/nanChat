import { useLayoutEffect, useRef } from "react"

import { MessageBubble } from "@/components/chat/MessageBubble"
import type { Message } from "@/types/chat"

interface MessageListProps {
  conversationKey: string
  messages: Message[]
  isStreaming: boolean
  onSuggestion: (suggestion: string) => void
}

const suggestions = [
  "介绍一下这个项目",
  "如何设计一个 AI Chat 的后端？",
  "给我一个简洁的产品创意",
]

export function MessageList({ conversationKey, messages, isStreaming, onSuggestion }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const shouldAutoScrollRef = useRef(true)
  const pendingConversationScrollRef = useRef(false)

  const handleScroll = () => {
    const element = scrollRef.current
    if (!element) return

    const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight
    shouldAutoScrollRef.current = distanceFromBottom < 96
  }

  useLayoutEffect(() => {
    pendingConversationScrollRef.current = true
    shouldAutoScrollRef.current = true
  }, [conversationKey])

  useLayoutEffect(() => {
    const element = scrollRef.current
    if (!element) return

    if (pendingConversationScrollRef.current) {
      if (messages.length === 0) return

      element.scrollTo({
        top: element.scrollHeight,
        behavior: "auto",
      })
      pendingConversationScrollRef.current = false
      return
    }

    if (!shouldAutoScrollRef.current) return

    element.scrollTo({
      top: element.scrollHeight,
      behavior: isStreaming ? "auto" : "smooth",
    })
  }, [conversationKey, messages, isStreaming])

  return (
    <div className="min-h-0 flex-1 overflow-y-auto" onScroll={handleScroll} ref={scrollRef}>
      {messages.length === 0 ? (
        <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col items-center justify-center px-6 py-12">
          <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-foreground text-background">
            <span className="text-lg font-semibold">✦</span>
          </div>
          <h1 className="text-center text-2xl font-semibold tracking-tight sm:text-3xl">How can I help you today?</h1>
          <p className="mt-3 max-w-md text-center text-sm leading-6 text-muted-foreground">
            输入消息后，前端会通过 SSE 接收 LongCat 的实时回复。
          </p>
          <div className="mt-8 grid w-full max-w-2xl gap-2 sm:grid-cols-3">
            {suggestions.map((suggestion) => (
              <button
                className="rounded-xl border border-border bg-background p-3 text-left text-xs leading-5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                key={suggestion}
                onClick={() => onSuggestion(suggestion)}
                type="button"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col gap-6 px-6 py-8">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </div>
      )}
    </div>
  )
}
