import type { FormEvent, KeyboardEvent } from "react"
import { ArrowUp, BookOpen, Square } from "lucide-react"

import { ModelSettingsPopover } from "@/components/chat/ModelSettingsPopover"
import { Button } from "@/components/ui/button"
import { PromptInput, PromptInputActions, PromptInputTextarea } from "@/components/ui/prompt-input"
import type { ContextUsage, ModelOption, ThinkingLevel } from "@/types/chat"

interface ChatComposerProps {
  value: string
  disabled?: boolean
  isStreaming?: boolean
  models: ModelOption[]
  selectedModelId: string
  thinkingLevel: ThinkingLevel
  ragEnabled: boolean
  contextUsage: ContextUsage
  onChange: (value: string) => void
  onModelChange: (modelId: string) => void
  onThinkingLevelChange: (thinkingLevel: ThinkingLevel) => void
  onRagEnabledChange: (enabled: boolean) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onStop: () => void
}

export function ChatComposer({
  value,
  disabled,
  isStreaming,
  models,
  selectedModelId,
  thinkingLevel,
  ragEnabled,
  contextUsage,
  onChange,
  onModelChange,
  onThinkingLevelChange,
  onRagEnabledChange,
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
    <div className="mx-auto w-full max-w-3xl shrink-0 px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-6 sm:pb-6">
      <PromptInput onSubmit={onSubmit}>
        <PromptInputTextarea
          disabled={disabled}
          onChange={onChange}
          onKeyDown={handleKeyDown}
          placeholder="Message AI Chat..."
          value={value}
        />
        <PromptInputActions>
          <span className="mr-auto hidden px-2 text-xs text-muted-foreground sm:inline">
            Enter 发送 · Shift + Enter 换行
          </span>
          <button
            aria-checked={ragEnabled}
            aria-label={ragEnabled ? "关闭知识库检索" : "开启知识库检索"}
            className={[
              "inline-flex h-9 items-center gap-1.5 rounded-lg border px-2.5 text-xs transition-colors sm:h-8",
              ragEnabled
                ? "border-foreground bg-foreground text-background"
                : "border-transparent text-muted-foreground hover:border-border hover:text-foreground",
              "disabled:pointer-events-none disabled:opacity-50",
            ].join(" ")}
            disabled={disabled}
            onClick={() => onRagEnabledChange(!ragEnabled)}
            role="switch"
            title={ragEnabled ? "已开启知识库检索" : "开启知识库检索"}
            type="button"
          >
            <BookOpen className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">知识库</span>
          </button>
          <ModelSettingsPopover
            contextUsage={contextUsage}
            disabled={disabled}
            models={models}
            onModelChange={onModelChange}
            onThinkingLevelChange={onThinkingLevelChange}
            selectedModelId={selectedModelId}
            thinkingLevel={thinkingLevel}
          />
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
