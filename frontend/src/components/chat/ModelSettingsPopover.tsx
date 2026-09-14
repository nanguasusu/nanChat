import { useEffect, useRef, useState } from "react"
import { Check, ChevronDown, ChevronRight, RotateCcw } from "lucide-react"

import { ContextUsageIndicator } from "@/components/chat/ContextUsageIndicator"
import type { ContextUsage, ModelOption, ThinkingLevel } from "@/types/chat"

interface ModelSettingsPopoverProps {
  disabled?: boolean
  models: ModelOption[]
  selectedModelId: string
  thinkingLevel: ThinkingLevel
  contextUsage: ContextUsage
  onModelChange: (modelId: string) => void
  onThinkingLevelChange: (thinkingLevel: ThinkingLevel) => void
}

const thinkingLevelLabels: Record<ThinkingLevel, string> = {
  off: "关闭",
  low: "低",
  medium: "中",
  high: "高",
  xhigh: "极高",
}

function ThinkingIntensitySlider({
  levels,
  value,
  onChange,
}: {
  levels: ThinkingLevel[]
  value: ThinkingLevel
  onChange: (value: ThinkingLevel) => void
}) {
  const levelIndex = Math.max(0, levels.indexOf(value))
  const progress = levels.length > 1 ? (levelIndex / (levels.length - 1)) * 100 : 100

  return (
    <div className="w-full px-4 py-3 md:w-64">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>思考强度</span>
        <span className="font-medium text-foreground">{thinkingLevelLabels[value]}</span>
      </div>
      <div className="relative mt-5 h-8">
        <div className="absolute left-1 right-1 top-3 h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-gradient-to-r from-violet-300 via-violet-500 to-fuchsia-500 transition-[width] duration-200"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="pointer-events-none absolute left-1 right-1 top-2.5 flex justify-between">
          {levels.map((level, index) => (
            <span
              className={`thinking-particle h-3 w-3 rounded-full transition-all duration-200 ${
                index <= levelIndex
                  ? "bg-violet-300 shadow-[0_0_10px_3px_rgba(167,139,250,0.8)]"
                  : "bg-muted-foreground/30"
              }`}
              key={level}
            />
          ))}
        </div>
        <input
          aria-label="思考强度"
          className="thinking-range absolute inset-0 h-8 w-full cursor-pointer"
          max={Math.max(0, levels.length - 1)}
          min={0}
          onChange={(event) => onChange(levels[Number(event.target.value)])}
          type="range"
          value={levelIndex}
        />
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-muted-foreground">
        <span>{thinkingLevelLabels[levels[0]]}</span>
        <span>{thinkingLevelLabels[levels[levels.length - 1]]}</span>
      </div>
      <p className="mt-3 text-[11px] leading-4 text-muted-foreground">
        强度越高，为模型分配的回答 token 预算越大。
      </p>
    </div>
  )
}

export function ModelSettingsPopover({
  disabled,
  models,
  selectedModelId,
  thinkingLevel,
  contextUsage,
  onModelChange,
  onThinkingLevelChange,
}: ModelSettingsPopoverProps) {
  const rootRef = useRef<HTMLDivElement>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [activePanel, setActivePanel] = useState<"model" | "thinking">("model")
  const selectedModel = models.find((model) => model.id === selectedModelId) ?? models[0]
  const thinkingLevels = selectedModel?.thinkingLevels ?? ["off", "low", "medium", "high", "xhigh"]
  const selectedThinkingLevel = thinkingLevels.includes(thinkingLevel)
    ? thinkingLevel
    : thinkingLevels[Math.min(2, thinkingLevels.length - 1)]

  useEffect(() => {
    if (!isOpen) return

    const handlePointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setIsOpen(false)
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false)
    }

    document.addEventListener("pointerdown", handlePointerDown)
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown)
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [isOpen])

  const resetSettings = () => {
    if (!models[0]) return
    onModelChange(models[0].id)
    onThinkingLevelChange("medium")
  }

  return (
    <div className="flex items-center gap-1" ref={rootRef}>
      <ContextUsageIndicator usage={contextUsage} />
      <div className="relative">
        <button
          aria-expanded={isOpen}
          aria-haspopup="dialog"
          aria-label="模型和思考设置"
          className="flex h-9 max-w-[11rem] items-center gap-1.5 rounded-md px-2 text-sm transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 sm:h-8 sm:max-w-none"
          disabled={disabled}
          onClick={() => setIsOpen((value) => !value)}
          type="button"
        >
          <span className="min-w-0 truncate">{selectedModel?.label ?? "选择模型"}</span>
          <span className="hidden shrink-0 text-muted-foreground sm:inline">
            {thinkingLevelLabels[selectedThinkingLevel]}
          </span>
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        </button>

        {isOpen && (
          <button
            aria-label="关闭模型和思考设置"
            className="fixed inset-0 z-30 bg-black/20 md:hidden"
            onClick={() => setIsOpen(false)}
            type="button"
          />
        )}

        {isOpen && (
          <div
            aria-label="模型和思考设置面板"
            className="fixed inset-x-3 bottom-[max(5.5rem,calc(env(safe-area-inset-bottom)+4.5rem))] z-40 flex max-h-[min(28rem,70dvh)] flex-col overflow-hidden rounded-2xl border border-border bg-background/95 shadow-2xl backdrop-blur md:absolute md:inset-auto md:bottom-[calc(100%+0.75rem)] md:right-0 md:z-30 md:max-h-none md:flex-row"
            role="dialog"
          >
            <div className="w-full shrink-0 border-b border-border p-2 md:w-52 md:border-b-0 md:border-r">
              <button
                className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm transition-colors ${
                  activePanel === "model" ? "bg-muted" : "hover:bg-muted/70"
                }`}
                onClick={() => setActivePanel("model")}
                type="button"
              >
                <span className="flex-1">模型</span>
                <span className="max-w-24 truncate text-muted-foreground">{selectedModel?.label}</span>
                <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              </button>
              <button
                className={`mt-1 flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm transition-colors ${
                  activePanel === "thinking" ? "bg-muted" : "hover:bg-muted/70"
                }`}
                onClick={() => setActivePanel("thinking")}
                type="button"
              >
                <span className="flex-1">思考强度</span>
                <span className="text-muted-foreground">{thinkingLevelLabels[selectedThinkingLevel]}</span>
                <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              </button>
              <div className="my-2 border-t border-border" />
              <button
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                onClick={resetSettings}
                type="button"
              >
                <RotateCcw className="h-4 w-4" />
                <span>重置为默认设置</span>
              </button>
            </div>
            <div className="min-h-48 w-full overflow-y-auto md:w-64">
              {activePanel === "model" ? (
                <div className="p-2">
                  {models.map((model) => (
                    <button
                      className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted"
                      key={model.id}
                      onClick={() => onModelChange(model.id)}
                      type="button"
                    >
                      <span className="flex-1">{model.label}</span>
                      {model.id === selectedModelId && <Check className="h-4 w-4" />}
                    </button>
                  ))}
                </div>
              ) : (
                <ThinkingIntensitySlider
                  levels={thinkingLevels}
                  onChange={onThinkingLevelChange}
                  value={selectedThinkingLevel}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
