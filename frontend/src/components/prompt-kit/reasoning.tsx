import { ChevronDownIcon } from "lucide-react"
import { createContext, useContext, useEffect, useRef, useState } from "react"

import { Markdown } from "@/components/prompt-kit/markdown"
import { cn } from "@/lib/utils"

type ReasoningContextType = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
}

const ReasoningContext = createContext<ReasoningContextType | undefined>(undefined)

function useReasoningContext() {
  const context = useContext(ReasoningContext)
  if (!context) {
    throw new Error("useReasoningContext must be used within a Reasoning provider")
  }
  return context
}

export type ReasoningProps = {
  children: React.ReactNode
  className?: string
  open?: boolean
  onOpenChange?: (open: boolean) => void
  isStreaming?: boolean
}

function Reasoning({
  children,
  className,
  open,
  onOpenChange,
  isStreaming,
}: ReasoningProps) {
  const [internalOpen, setInternalOpen] = useState(false)
  const [wasAutoOpened, setWasAutoOpened] = useState(false)
  const isControlled = open !== undefined
  const isOpen = isControlled ? open : internalOpen

  const handleOpenChange = (newOpen: boolean) => {
    if (!isControlled) setInternalOpen(newOpen)
    onOpenChange?.(newOpen)
  }

  useEffect(() => {
    if (isStreaming && !wasAutoOpened) {
      if (!isControlled) setInternalOpen(true)
      setWasAutoOpened(true)
    }

    if (!isStreaming && wasAutoOpened) {
      if (!isControlled) setInternalOpen(false)
      setWasAutoOpened(false)
    }
  }, [isControlled, isStreaming, wasAutoOpened])

  return (
    <ReasoningContext.Provider value={{ isOpen, onOpenChange: handleOpenChange }}>
      <div className={className}>{children}</div>
    </ReasoningContext.Provider>
  )
}

export type ReasoningTriggerProps = {
  children: React.ReactNode
  className?: string
} & React.HTMLAttributes<HTMLButtonElement>

function ReasoningTrigger({ children, className, ...props }: ReasoningTriggerProps) {
  const { isOpen, onOpenChange } = useReasoningContext()

  return (
    <button
      className={cn("flex cursor-pointer items-center gap-2", className)}
      onClick={() => onOpenChange(!isOpen)}
      type="button"
      {...props}
    >
      <span className="text-primary">{children}</span>
      <ChevronDownIcon className={cn("h-4 w-4 transition-transform", isOpen && "rotate-180")} />
    </button>
  )
}

export type ReasoningContentProps = {
  children: React.ReactNode
  className?: string
  markdown?: boolean
  contentClassName?: string
} & React.HTMLAttributes<HTMLDivElement>

function ReasoningContent({
  children,
  className,
  contentClassName,
  markdown = false,
  ...props
}: ReasoningContentProps) {
  const contentRef = useRef<HTMLDivElement>(null)
  const innerRef = useRef<HTMLDivElement>(null)
  const { isOpen } = useReasoningContext()

  useEffect(() => {
    if (!contentRef.current || !innerRef.current) return

    const observer = new ResizeObserver(() => {
      if (contentRef.current && innerRef.current && isOpen) {
        contentRef.current.style.maxHeight = `${innerRef.current.scrollHeight}px`
      }
    })

    observer.observe(innerRef.current)
    if (isOpen) contentRef.current.style.maxHeight = `${innerRef.current.scrollHeight}px`

    return () => observer.disconnect()
  }, [isOpen])

  const content = markdown ? <Markdown>{children as string}</Markdown> : children

  return (
    <div
      className={cn("overflow-hidden transition-[max-height] duration-150 ease-out", className)}
      ref={contentRef}
      style={{ maxHeight: isOpen ? contentRef.current?.scrollHeight : "0px" }}
      {...props}
    >
      <div
        className={cn("prose prose-sm text-muted-foreground dark:prose-invert", contentClassName)}
        ref={innerRef}
      >
        {content}
      </div>
    </div>
  )
}

export { Reasoning, ReasoningContent, ReasoningTrigger }
