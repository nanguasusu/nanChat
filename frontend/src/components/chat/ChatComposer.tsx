import type { FormEvent, KeyboardEvent } from "react"
import { ArrowUp, Square } from "lucide-react"

import { Button } from "@/components/ui/button"
import { PromptInput, PromptInputActions, PromptInputTextarea } from "@/components/ui/prompt-input"

interface ChatComposerProps {
  value: string
  disabled?: boolean
  isStreaming?: boolean
  onChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onStop: () => void
}

export function ChatComposer({
  value,
  disabled,
  isStreaming,
  onChange,
  onSubmit,
  onStop,
}: ChatComposerProps) {
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl shrink-0 px-4 pb-4 sm:px-6 sm:pb-6">
      <PromptInput onSubmit={onSubmit}>
        <PromptInputTextarea
          disabled={disabled}
          onChange={onChange}
          onKeyDown={handleKeyDown}
          placeholder="Message AI Chat..."
          value={value}
        />
        <PromptInputActions>
          <span className="mr-auto px-2 text-xs text-muted-foreground">Enter 发送 · Shift + Enter 换行</span>
          {isStreaming ? (
            <Button aria-label="停止生成" onClick={onStop} size="icon" type="button" variant="outline">
              <Square className="h-3.5 w-3.5 fill-current" />
            </Button>
          ) : (
            <Button aria-label="发送消息" disabled={disabled || !value.trim()} size="icon" type="submit">
              <ArrowUp className="h-4 w-4" />
            </Button>
          )}
        </PromptInputActions>
      </PromptInput>
    </div>
  )
}
