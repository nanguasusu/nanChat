import { useEffect } from "react"
import { Settings, X } from "lucide-react"

import { Button } from "@/components/ui/button"

interface SettingsDialogProps {
  isOpen: boolean
  agenticRagEnabled: boolean
  queryRewriteEnabled: boolean
  onClose: () => void
  onAgenticRagEnabledChange: (enabled: boolean) => void
  onQueryRewriteEnabledChange: (enabled: boolean) => void
}

export function SettingsDialog({
  isOpen,
  agenticRagEnabled,
  queryRewriteEnabled,
  onClose,
  onAgenticRagEnabledChange,
  onQueryRewriteEnabledChange,
}: SettingsDialogProps) {
  const effectiveQueryRewriteEnabled = queryRewriteEnabled && !agenticRagEnabled

  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose()
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      aria-label="设置"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4 backdrop-blur-[2px]"
      onClick={onClose}
      role="presentation"
    >
      <div
        aria-labelledby="settings-dialog-title"
        aria-modal="true"
        className="flex max-h-[min(36rem,calc(100dvh-2rem))] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-border bg-background shadow-2xl"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="flex items-center gap-2">
            <Settings className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold" id="settings-dialog-title">
              设置
            </h2>
          </div>
          <Button aria-label="关闭设置" onClick={onClose} size="icon" variant="ghost">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto p-5">
          <section>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
              知识库检索
            </p>
            <div className="mt-3 flex items-start gap-4 rounded-xl border border-border p-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium">Agentic RAG</p>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                    可选
                  </span>
                </div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  先规划检索任务，再按任务补充资料，适合复杂、多步骤或需要完整覆盖的问题。
                  开启后会增加检索和模型调用时间，并自动停用 Query Rewrite。
                </p>
              </div>
              <button
                aria-checked={agenticRagEnabled}
                aria-label={agenticRagEnabled ? "关闭 Agentic RAG" : "开启 Agentic RAG"}
                className={`relative mt-0.5 h-6 w-11 shrink-0 overflow-hidden rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  agenticRagEnabled ? "bg-foreground" : "bg-muted"
                }`}
                onClick={() => onAgenticRagEnabledChange(!agenticRagEnabled)}
                role="switch"
                type="button"
              >
                <span
                  className={`absolute left-1 top-1 h-4 w-4 rounded-full transition-transform ${
                    agenticRagEnabled
                      ? "translate-x-5 bg-background"
                      : "translate-x-0 bg-muted-foreground/60"
                  }`}
                />
              </button>
            </div>
            <div className="mt-3 flex items-start gap-4 rounded-xl border border-border p-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium">Query Rewrite</p>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                    可选
                  </span>
                </div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  先将问题改写成更适合检索的独立问题，适用于“那这个怎么办”等上下文问题。
                  开启后会增加一次模型调用。
                </p>
              </div>
              <button
                aria-checked={effectiveQueryRewriteEnabled}
                aria-label={effectiveQueryRewriteEnabled ? "关闭 Query Rewrite" : "开启 Query Rewrite"}
                className={`relative mt-0.5 h-6 w-11 shrink-0 overflow-hidden rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 ${
                  effectiveQueryRewriteEnabled ? "bg-foreground" : "bg-muted"
                }`}
                disabled={agenticRagEnabled}
                onClick={() => onQueryRewriteEnabledChange(!queryRewriteEnabled)}
                role="switch"
                type="button"
              >
                <span
                  className={`absolute left-1 top-1 h-4 w-4 rounded-full transition-transform ${
                    effectiveQueryRewriteEnabled
                      ? "translate-x-5 bg-background"
                      : "translate-x-0 bg-muted-foreground/60"
                  }`}
                />
              </button>
            </div>
            <p className="mt-3 text-[11px] leading-4 text-muted-foreground">
              Query Rewrite 只在标准 RAG 下生效；Agentic RAG 开启时不会调用它。两种模式都需要同时开启输入框的“知识库”开关。
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
