import { useEffect } from "react"
import { FileText, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { Citation } from "@/types/chat"

interface CitationDrawerProps {
  citation: Citation | null
  onClose: () => void
}

function formatPages(citation: Citation) {
  if (citation.pageStart === null) return "无页码"
  if (citation.pageStart === citation.pageEnd) return `第 ${citation.pageStart} 页`
  return `第 ${citation.pageStart}-${citation.pageEnd} 页`
}

function formatScore(citation: Citation) {
  const label = citation.scoreType === "reranker" ? "重排分数" : "融合分数"
  return `${label}：${citation.score.toFixed(3)}`
}

export function CitationDrawer({ citation, onClose }: CitationDrawerProps) {
  useEffect(() => {
    if (!citation) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose()
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [citation, onClose])

  if (!citation) return null

  return (
    <>
      <button
        aria-label="关闭引用抽屉"
        className="fixed inset-0 z-40 bg-black/20"
        onClick={onClose}
        type="button"
      />
      <aside
        aria-label="引用内容"
        aria-modal="true"
        className="fixed inset-x-0 bottom-0 z-50 flex max-h-[85dvh] w-full flex-col rounded-t-2xl border-t border-border bg-background pb-[env(safe-area-inset-bottom)] shadow-2xl md:inset-y-0 md:right-0 md:max-h-none md:max-w-[32rem] md:rounded-none md:border-l md:border-t-0 md:pb-0"
        role="dialog"
      >
        <div className="flex shrink-0 justify-center pt-2 md:hidden">
          <span className="h-1 w-10 rounded-full bg-border" />
        </div>
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm font-medium">
              <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate">{citation.filename}</span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {formatPages(citation)} · 命中 {citation.hitCount} 个子块
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {formatScore(citation)}
            </p>
          </div>
          <Button
            aria-label="关闭引用抽屉"
            className="shrink-0 text-muted-foreground"
            onClick={onClose}
            size="icon"
            variant="ghost"
          >
            <X className="h-4 w-4" />
          </Button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          <p className="whitespace-pre-wrap break-words text-sm leading-7 text-foreground">
            {citation.content}
          </p>
        </div>
      </aside>
    </>
  )
}
