import { ChevronRight } from "lucide-react"

import { TextShimmer } from "@/components/prompt-kit/text-shimmer"
import { cn } from "@/lib/utils"

type ThinkingBarProps = {
  className?: string
  text?: string
  onStop?: () => void
  stopLabel?: string
  onClick?: () => void
}

export function ThinkingBar({
  className,
  text = "Thinking",
  onStop,
  stopLabel = "Answer now",
  onClick,
}: ThinkingBarProps) {
  return (
    <div className={cn("flex w-full items-center justify-between", className)}>
      {onClick ? (
        <button
          className="flex items-center gap-1 text-sm transition-opacity hover:opacity-80"
          onClick={onClick}
          type="button"
        >
          <TextShimmer className="font-medium">{text}</TextShimmer>
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        </button>
      ) : (
        <TextShimmer className="cursor-default font-medium">{text}</TextShimmer>
      )}
      {onStop ? (
        <button
          className="border-b border-dotted border-muted-foreground/50 text-sm text-muted-foreground transition-colors hover:border-foreground hover:text-foreground"
          onClick={onStop}
          type="button"
        >
          {stopLabel}
        </button>
      ) : null}
    </div>
  )
}
