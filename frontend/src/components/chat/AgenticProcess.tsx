import { useEffect, useState } from "react"
import {
  Check,
  ChevronDown,
  Circle,
  Loader2,
  RefreshCw,
  TriangleAlert,
} from "lucide-react"

import type { AgenticStageEvent } from "@/types/chat"
import { cn } from "@/lib/utils"

type AgenticStepStatus = "running" | "retrying" | "completed" | "error"

interface AgenticStep {
  id: string
  label: string
  status: AgenticStepStatus
  attempts?: number
}

interface AgenticProcessProps {
  events: AgenticStageEvent[]
  isStreaming: boolean
}

function stepId(event: AgenticStageEvent) {
  return event.taskId ? `task:${event.taskId}` : event.stage
}

function stepLabel(event: AgenticStageEvent) {
  if (event.stage === "initial_retrieval") {
    return event.parentCount === undefined
      ? "初步检索知识库"
      : `初步检索知识库（${event.parentCount} 条资料）`
  }
  if (event.stage === "planning") {
    return event.taskCount === undefined
      ? "分析问题并规划检索任务"
      : `分析问题并规划检索任务（${event.taskCount} 个）`
  }
  if (event.stage === "synthesis") return "综合检索结果并生成回答"
  return event.label || "执行检索任务"
}

function toStepStatus(event: AgenticStageEvent): AgenticStepStatus {
  if (event.status === "start") return "running"
  if (event.status === "retry") return "retrying"
  return event.resultStatus === "error" ? "error" : "completed"
}

function buildSteps(events: AgenticStageEvent[]) {
  const steps: AgenticStep[] = []
  const stepById = new Map<string, AgenticStep>()

  for (const event of events) {
    const id = stepId(event)
    const current = stepById.get(id)
    if (!current) {
      const step = {
        id,
        label: stepLabel(event),
        status: toStepStatus(event),
        attempts: event.attempts,
      }
      steps.push(step)
      stepById.set(id, step)
      continue
    }

    if (
      event.label ||
      event.taskCount !== undefined ||
      event.parentCount !== undefined
    ) {
      current.label = stepLabel(event)
    }
    current.status = toStepStatus(event)
    current.attempts = event.attempts ?? current.attempts
  }

  return steps
}

function StepIcon({ status }: { status: AgenticStepStatus }) {
  if (status === "completed") {
    return <Check className="h-3.5 w-3.5 text-foreground" />
  }
  if (status === "retrying") {
    return <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />
  }
  if (status === "error") {
    return <TriangleAlert className="h-3.5 w-3.5 text-destructive" />
  }
  return <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
}

export function AgenticProcess({ events, isStreaming }: AgenticProcessProps) {
  const [isOpen, setIsOpen] = useState(true)
  const steps = buildSteps(events)
  const taskCount = events.filter(
    (event) => event.stage === "task" && event.status === "start",
  ).length
  const retryCount = events.filter((event) => event.status === "retry").length
  const hasError = steps.some((step) => step.status === "error")
  const isComplete = events.some(
    (event) => event.stage === "synthesis" && event.status === "done",
  )

  useEffect(() => {
    setIsOpen(isStreaming)
  }, [isStreaming])

  if (steps.length === 0) return null

  const summary = isStreaming
    ? "Agentic RAG 检索中"
    : hasError
      ? "Agentic RAG 检索未完全完成"
      : isComplete
        ? `Agentic RAG 已完成 · ${taskCount} 个任务${retryCount ? ` · ${retryCount} 次补充检索` : ""}`
        : "Agentic RAG 检索过程"

  return (
    <div className="mb-3 text-sm text-muted-foreground">
      <button
        aria-expanded={isOpen}
        className="flex cursor-pointer items-center gap-2 text-left transition-colors hover:text-foreground"
        onClick={() => setIsOpen((value) => !value)}
        type="button"
      >
        {isStreaming ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : hasError ? (
          <TriangleAlert className="h-3.5 w-3.5 text-destructive" />
        ) : (
          <Circle className="h-2.5 w-2.5 fill-current" />
        )}
        <span>{summary}</span>
        <ChevronDown className={cn("h-4 w-4 transition-transform", isOpen && "rotate-180")} />
      </button>

      <div
        className={cn(
          "grid transition-[grid-template-rows] duration-200",
          isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        )}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="ml-1.5 mt-2 space-y-2 border-l border-primary/20 pl-4">
            {steps.map((step) => (
              <div className="flex items-start gap-2" key={step.id}>
                <span className="-ml-[1.4rem] mt-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-background">
                  <StepIcon status={step.status} />
                </span>
                <span className="min-w-0 leading-5">
                  {step.label}
                  {step.attempts && step.attempts > 1 && (
                    <span className="ml-1 text-xs text-muted-foreground/70">
                      · {step.attempts} 次
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
