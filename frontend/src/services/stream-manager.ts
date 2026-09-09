import type { Thread, ThinkingLevel } from "@/types/chat"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

interface StreamStartEvent {
  type: "start"
  thread_id: string
  assistant_message_id: string
  thread: Thread
}

interface StreamDeltaEvent {
  type: "delta"
  content: string
}

interface StreamReasoningDeltaEvent {
  type: "reasoning_delta"
  content: string
}

interface StreamThinkingCompleteEvent {
  type: "thinking_complete"
  thinking_duration_ms: number
}

interface StreamDoneEvent {
  type: "done"
  thread_id: string
  message_id: string
  thread: Thread
  thinking_duration_ms: number
}

interface StreamErrorEvent {
  type: "error"
  code: string
  message: string
}

type StreamEvent =
  | StreamStartEvent
  | StreamDeltaEvent
  | StreamReasoningDeltaEvent
  | StreamThinkingCompleteEvent
  | StreamDoneEvent
  | StreamErrorEvent

interface StreamCallbacks {
  onStart: (event: StreamStartEvent) => void
  onDelta: (event: StreamDeltaEvent) => void
  onReasoning: (event: StreamReasoningDeltaEvent) => void
  onThinkingComplete: (event: StreamThinkingCompleteEvent) => void
  onDone: (event: StreamDoneEvent) => void
  onError: (error: Error) => void
  onAborted: () => void
}

interface StartStreamOptions extends StreamCallbacks {
  conversationKey: string
  threadId: string | null
  message: string
  model: string
  thinkingLevel: ThinkingLevel
}

const activeStreams = new Map<string, AbortController>()

function parseSseEvent(block: string): StreamEvent | null {
  const data = block
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice("data:".length).trimStart())
    .join("\n")

  if (!data) return null
  return JSON.parse(data) as StreamEvent
}

function removeStream(key: string, controller: AbortController) {
  if (activeStreams.get(key) === controller) {
    activeStreams.delete(key)
  }
}

async function consumeStream(
  response: Response,
  controller: AbortController,
  callbacks: StreamCallbacks,
  initialKey: string,
) {
  const reader = response.body?.getReader()
  if (!reader) throw new Error("浏览器不支持流式响应。")

  const decoder = new TextDecoder()
  let buffer = ""
  let streamKey = initialKey
  let terminalEventReceived = false

  const handleEvent = (event: StreamEvent) => {
    if (event.type === "start") {
      const currentStream = activeStreams.get(streamKey)
      if (currentStream === controller && event.thread_id !== streamKey) {
        activeStreams.delete(streamKey)
        activeStreams.set(event.thread_id, controller)
        streamKey = event.thread_id
      }
      callbacks.onStart(event)
      return
    }

    if (event.type === "delta") {
      callbacks.onDelta(event)
      return
    }

    if (event.type === "reasoning_delta") {
      callbacks.onReasoning(event)
      return
    }

    if (event.type === "thinking_complete") {
      callbacks.onThinkingComplete(event)
      return
    }

    terminalEventReceived = true
    if (event.type === "done") {
      callbacks.onDone(event)
    } else {
      callbacks.onError(new Error(event.message))
    }
  }

  try {
    while (!terminalEventReceived) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })

      let separatorIndex = buffer.search(/\r?\n\r?\n/)
      while (separatorIndex !== -1) {
        const separator = buffer.match(/\r?\n\r?\n/)![0]
        const block = buffer.slice(0, separatorIndex)
        buffer = buffer.slice(separatorIndex + separator.length)
        const event = parseSseEvent(block)
        if (event) handleEvent(event)
        if (terminalEventReceived) break
        separatorIndex = buffer.search(/\r?\n\r?\n/)
      }

      if (done) {
        const finalEvent = parseSseEvent(buffer)
        if (finalEvent && !terminalEventReceived) handleEvent(finalEvent)
        break
      }
    }

    if (!terminalEventReceived && !controller.signal.aborted) {
      throw new Error("流式响应提前结束。")
    }
  } catch (error) {
    if (controller.signal.aborted) {
      callbacks.onAborted()
    } else {
      callbacks.onError(error instanceof Error ? error : new Error("流式请求失败。"))
    }
  } finally {
    reader.releaseLock()
    removeStream(streamKey, controller)
    removeStream(initialKey, controller)
  }
}

export function startChatStream({
  conversationKey,
  threadId,
  message,
  model,
  thinkingLevel,
  onStart,
  onDelta,
  onReasoning,
  onThinkingComplete,
  onDone,
  onError,
  onAborted,
}: StartStreamOptions) {
  if (activeStreams.has(conversationKey)) {
    onError(new Error("当前会话正在生成中。"))
    return
  }

  const controller = new AbortController()
  activeStreams.set(conversationKey, controller)

  void (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          thread_id: threadId,
          model,
          thinking_level: thinkingLevel,
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error("聊天请求失败，请检查后端服务。")
      }

      await consumeStream(
        response,
        controller,
        {
          onStart,
          onDelta,
          onReasoning,
          onThinkingComplete,
          onDone,
          onError,
          onAborted,
        },
        conversationKey,
      )
    } catch (error) {
      if (controller.signal.aborted) {
        onAborted()
      } else {
        onError(error instanceof Error ? error : new Error("流式请求失败。"))
      }
      removeStream(conversationKey, controller)
    }
  })()
}

export function stopChatStream(conversationKey: string) {
  activeStreams.get(conversationKey)?.abort()
}

export function isChatStreamActive(conversationKey: string) {
  return activeStreams.has(conversationKey)
}
