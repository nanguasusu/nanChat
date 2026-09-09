import { CircleGauge } from "lucide-react"

import { formatTokenCount } from "@/lib/context"
import type { ContextUsage } from "@/types/chat"

interface ContextUsageIndicatorProps {
  usage: ContextUsage
}

function usageColor(percent: number) {
  if (percent >= 90) return "text-destructive"
  if (percent >= 75) return "text-amber-600 dark:text-amber-400"
  return "text-muted-foreground"
}

export function ContextUsageIndicator({ usage }: ContextUsageIndicatorProps) {
  return (
    <div className="group relative">
      <button
        aria-label={`上下文窗口已使用 ${usage.percent}%`}
        className={`flex h-8 items-center gap-1 rounded-md px-2 text-xs transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${usageColor(usage.percent)}`}
        type="button"
      >
        <CircleGauge className="h-4 w-4" />
        <span>{usage.percent}%</span>
      </button>
      <div
        className="pointer-events-none invisible absolute bottom-full right-0 z-20 mb-2 w-56 rounded-xl bg-foreground px-3 py-2.5 text-left text-xs text-background opacity-0 shadow-lg transition-opacity group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100"
        role="tooltip"
      >
        <div className="font-medium">上下文窗口</div>
        <div className="mt-1.5 text-sm">
          {usage.percent}% 已用（剩余 {100 - usage.percent}%）
        </div>
        <div className="mt-1 text-background/70">
          已用 {formatTokenCount(usage.usedTokens)} tokens，共 {formatTokenCount(usage.maxTokens)}
        </div>
        {usage.estimated && <div className="mt-1 text-background/50">当前为估算值</div>}
      </div>
    </div>
  )
}
