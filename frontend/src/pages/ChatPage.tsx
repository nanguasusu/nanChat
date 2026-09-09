import { useEffect, useState } from "react"
import type { FormEvent } from "react"
import { PanelLeft, Sparkles } from "lucide-react"

import { ChatComposer } from "@/components/chat/ChatComposer"
import { MessageList } from "@/components/chat/MessageList"
import { NotificationToasts } from "@/components/layout/NotificationToasts"
import { Sidebar } from "@/components/layout/Sidebar"
import { Button } from "@/components/ui/button"
import { estimateContextUsage } from "@/lib/context"
import { deleteThread, getThreadMessages, listModels, listThreads } from "@/services/chat"
import { startChatStream, stopChatStream } from "@/services/stream-manager"
import { DEFAULT_MODEL, type Message, type Thread, type ThinkingLevel } from "@/types/chat"
import { NEW_CHAT_KEY, useChatStore } from "@/stores/chat-store"

const EMPTY_MESSAGES: Message[] = []

function createLocalMessageId(prefix: string) {
  return `${prefix}-${crypto.randomUUID()}`
}

export function ChatPage() {
  const threads = useChatStore((state) => state.threads)
  const models = useChatStore((state) => state.models)
  const activeThreadId = useChatStore((state) => state.activeThreadId)
  const activeConversationKey = useChatStore((state) => state.activeConversationKey)
  const messages = useChatStore(
    (state) => state.messagesByConversation[state.activeConversationKey] ?? EMPTY_MESSAGES,
  )
  const draft = useChatStore(
    (state) => state.drafts[state.activeConversationKey] ?? "",
  )
  const streamStatus = useChatStore(
    (state) => state.streamStatusByConversation[state.activeConversationKey] ?? "idle",
  )
  const streamStatusByConversation = useChatStore((state) => state.streamStatusByConversation)
  const modelByConversation = useChatStore((state) => state.modelByConversation)
  const thinkingLevelByConversation = useChatStore(
    (state) => state.thinkingLevelByConversation,
  )
  const setThreads = useChatStore((state) => state.setThreads)
  const setModels = useChatStore((state) => state.setModels)
  const upsertThread = useChatStore((state) => state.upsertThread)
  const setActiveConversation = useChatStore((state) => state.setActiveConversation)
  const setMessages = useChatStore((state) => state.setMessages)
  const addMessage = useChatStore((state) => state.addMessage)
  const appendMessageContent = useChatStore((state) => state.appendMessageContent)
  const appendMessageReasoningContent = useChatStore(
    (state) => state.appendMessageReasoningContent,
  )
  const replaceMessageId = useChatStore((state) => state.replaceMessageId)
  const setMessageStatus = useChatStore((state) => state.setMessageStatus)
  const setMessageStreamPhase = useChatStore((state) => state.setMessageStreamPhase)
  const setMessageThinkingDuration = useChatStore(
    (state) => state.setMessageThinkingDuration,
  )
  const setDraft = useChatStore((state) => state.setDraft)
  const setStreamStatus = useChatStore((state) => state.setStreamStatus)
  const setModel = useChatStore((state) => state.setModel)
  const setThinkingLevel = useChatStore((state) => state.setThinkingLevel)
  const migrateConversation = useChatStore((state) => state.migrateConversation)
  const removeThread = useChatStore((state) => state.removeThread)
  const addNotification = useChatStore((state) => state.addNotification)
  const [isDark, setIsDark] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const isStreaming = streamStatus === "streaming"
  const selectedModelId =
    modelByConversation[activeConversationKey] ?? models[0]?.id ?? DEFAULT_MODEL.id
  const selectedModel =
    models.find((model) => model.id === selectedModelId) ?? models[0] ?? DEFAULT_MODEL
  const thinkingLevel: ThinkingLevel =
    thinkingLevelByConversation[activeConversationKey] ?? "medium"
  const contextUsage = estimateContextUsage(
    messages,
    draft,
    selectedModel.contextWindowTokens,
  )

  useEffect(() => {
    let isMounted = true

    void (async () => {
      try {
        const [loadedThreads, loadedModels] = await Promise.all([listThreads(), listModels()])
        if (!isMounted) return

        setModels(loadedModels)
        setThreads(loadedThreads)
        const currentState = useChatStore.getState()
        const hasNewChatWork =
          currentState.drafts[NEW_CHAT_KEY] ||
          (currentState.messagesByConversation[NEW_CHAT_KEY]?.length ?? 0) > 0
        if (currentState.activeConversationKey !== NEW_CHAT_KEY || hasNewChatWork) return

        const latestThread = loadedThreads[0]
        if (!latestThread) return

        const loadedMessages = await getThreadMessages(latestThread.id)
        if (!isMounted) return

        setActiveConversation(latestThread.id, latestThread.id)
        setMessages(latestThread.id, loadedMessages)
      } catch (error) {
        if (!isMounted) return
        setLoadError(error instanceof Error ? error.message : "加载会话失败。")
      }
    })()

    return () => {
      isMounted = false
    }
  }, [setActiveConversation, setMessages, setModels, setThreads])

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark)
  }, [isDark])

  const handleNewChat = () => {
    setLoadError(null)
    setActiveConversation(NEW_CHAT_KEY, null)
  }

  const handleSelectThread = async (threadId: string) => {
    if (threadId === activeThreadId) return

    setLoadError(null)
    setActiveConversation(threadId, threadId)
    const currentState = useChatStore.getState()
    if (currentState.messagesByConversation[threadId]) return

    try {
      const loadedMessages = await getThreadMessages(threadId)
      const latestState = useChatStore.getState()
      if (
        latestState.activeConversationKey === threadId &&
        latestState.streamStatusByConversation[threadId] !== "streaming"
      ) {
        setMessages(threadId, loadedMessages)
      }
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "加载会话失败。")
    }
  }

  const handleDeleteThread = async (thread: Thread) => {
    if (streamStatusByConversation[thread.id] === "streaming") {
      addNotification({ type: "error", message: "请先停止该会话的生成，再删除会话。" })
      return
    }

    if (!window.confirm(`确定删除“${thread.title}”吗？该会话的消息也会被删除。`)) return

    try {
      setLoadError(null)
      await deleteThread(thread.id)
      const wasActive = activeThreadId === thread.id
      removeThread(thread.id)

      if (wasActive) {
        setActiveConversation(NEW_CHAT_KEY, null)
      }
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "删除会话失败。")
    }
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const content = draft.trim()
    if (!content || isStreaming) return

    const conversationKey = activeConversationKey
    const threadId = activeThreadId
    const model = selectedModel.id
    const requestThinkingLevel = thinkingLevel
    const localAssistantMessageId = createLocalMessageId("assistant")
    let streamConversationKey = conversationKey
    let streamAssistantMessageId = localAssistantMessageId

    addMessage(conversationKey, { id: createLocalMessageId("user"), role: "user", content })
    addMessage(conversationKey, {
      id: localAssistantMessageId,
      role: "assistant",
      content: "",
      reasoningContent: "",
      streamPhase: "thinking",
      status: "streaming",
    })
    setDraft(conversationKey, "")
    setStreamStatus(conversationKey, "streaming")

    startChatStream({
      conversationKey,
      threadId,
      message: content,
      model,
      thinkingLevel: requestThinkingLevel,
      onStart: (event) => {
        replaceMessageId(
          streamConversationKey,
          streamAssistantMessageId,
          event.assistant_message_id,
        )
        migrateConversation(streamConversationKey, event.thread_id, event.thread_id)
        streamConversationKey = event.thread_id
        streamAssistantMessageId = event.assistant_message_id
        upsertThread(event.thread)
      },
      onDelta: (event) => {
        setMessageStreamPhase(
          streamConversationKey,
          streamAssistantMessageId,
          "answering",
        )
        appendMessageContent(streamConversationKey, streamAssistantMessageId, event.content)
      },
      onReasoning: (event) => {
        appendMessageReasoningContent(
          streamConversationKey,
          streamAssistantMessageId,
          event.content,
        )
      },
      onThinkingComplete: (event) => {
        setMessageStreamPhase(
          streamConversationKey,
          streamAssistantMessageId,
          "answering",
        )
        setMessageThinkingDuration(
          streamConversationKey,
          streamAssistantMessageId,
          event.thinking_duration_ms,
        )
      },
      onDone: (event) => {
        setMessageThinkingDuration(
          streamConversationKey,
          streamAssistantMessageId,
          event.thinking_duration_ms,
        )
        setMessageStatus(streamConversationKey, streamAssistantMessageId, "completed")
        setStreamStatus(streamConversationKey, "completed")
        upsertThread(event.thread)
        addNotification({
          type: "success",
          message: `“${event.thread.title}” 回复完成`,
        })
      },
      onError: (error) => {
        setMessageStatus(streamConversationKey, streamAssistantMessageId, "error")
        setStreamStatus(streamConversationKey, "error")
        addNotification({
          type: "error",
          message: `“${useChatStore.getState().threads.find((thread) => thread.id === streamConversationKey)?.title ?? "当前会话"}” 生成失败：${error.message}`,
        })
      },
      onAborted: () => {
        setMessageStatus(streamConversationKey, streamAssistantMessageId, "aborted")
        setStreamStatus(streamConversationKey, "aborted")
      },
    })
  }

  return (
    <div className="flex h-screen min-h-0 flex-col overflow-hidden bg-background text-foreground md:flex-row">
      {isSidebarOpen && (
        <button
          aria-label="关闭侧边栏"
          className="fixed inset-0 z-30 bg-black/20 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
          type="button"
        />
      )}
      <Sidebar
        activeThreadId={activeThreadId}
        isDark={isDark}
        isOpen={isSidebarOpen}
        onDeleteThread={handleDeleteThread}
        onNewChat={handleNewChat}
        onSelectThread={handleSelectThread}
        onToggleTheme={() => setIsDark((value) => !value)}
        streamStatusByConversation={streamStatusByConversation}
        threads={threads}
      />
      <main className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4 sm:px-6">
          <div className="flex items-center gap-1">
            <Button
              aria-controls="chat-sidebar"
              aria-expanded={isSidebarOpen}
              aria-label={isSidebarOpen ? "关闭侧边栏" : "打开侧边栏"}
              className="text-muted-foreground"
              onClick={() => setIsSidebarOpen((value) => !value)}
              size="icon"
              variant="ghost"
            >
              <PanelLeft className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Minimal workspace</span>
          </div>
        </header>

        <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
          {loadError && (
            <div className="border-b border-border bg-muted px-4 py-2 text-center text-xs text-muted-foreground">
              {loadError}
            </div>
          )}
          <MessageList
            conversationKey={activeConversationKey}
            messages={messages}
            onSuggestion={(value) => setDraft(activeConversationKey, value)}
            isStreaming={isStreaming}
          />
          <ChatComposer
            disabled={isStreaming}
            isStreaming={isStreaming}
            models={models}
            selectedModelId={selectedModel.id}
            thinkingLevel={thinkingLevel}
            contextUsage={contextUsage}
            onChange={(value) => setDraft(activeConversationKey, value)}
            onModelChange={(modelId) => setModel(activeConversationKey, modelId)}
            onThinkingLevelChange={(level) => setThinkingLevel(activeConversationKey, level)}
            onStop={() => stopChatStream(activeConversationKey)}
            onSubmit={handleSubmit}
            value={draft}
          />
        </section>
      </main>
      <NotificationToasts />
    </div>
  )
}
