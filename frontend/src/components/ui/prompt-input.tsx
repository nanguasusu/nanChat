import type { FormEvent, KeyboardEvent, ReactNode } from "react"

import { cn } from "@/lib/utils"
import { Textarea } from "@/components/ui/textarea"

interface PromptInputProps {
  children: ReactNode
  className?: string
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

function PromptInput({ children, className, onSubmit }: PromptInputProps) {
  return (
    <form
      className={cn(
        "rounded-2xl border border-border bg-background p-2 shadow-sm transition-shadow focus-within:ring-2 focus-within:ring-ring/20",
        className,
      )}
      onSubmit={onSubmit}
    >
      {children}
    </form>
  )
}

interface PromptInputTextareaProps {
  value: string
  onChange: (value: string) => void
  onKeyDown?: (event: KeyboardEvent<HTMLTextAreaElement>) => void
  placeholder?: string
  disabled?: boolean
}

function PromptInputTextarea({
  value,
  onChange,
  onKeyDown,
  placeholder,
  disabled,
}: PromptInputTextareaProps) {
  return (
    <Textarea
      aria-label="消息输入框"
      className="min-h-12 resize-none border-0 bg-transparent px-3 py-2.5 shadow-none focus-visible:ring-0"
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={onKeyDown}
      placeholder={placeholder}
      value={value}
    />
  )
}

function PromptInputActions({ children }: { children: ReactNode }) {
  return <div className="flex items-center justify-end gap-1 px-1 pb-1">{children}</div>
}

export { PromptInput, PromptInputActions, PromptInputTextarea }

