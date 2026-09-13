import { create } from "zustand"

import {
  DEFAULT_MODEL,
  type Message,
  type MessageStatus,
  type MessageStreamPhase,
  type AgenticStageEvent,
  type Citation,
  type ModelOption,
  type Thread,
  type ThinkingLevel,
} from "@/types/chat"

export const NEW_CHAT_KEY = "__new_chat__"

export type StreamStatus =
  | "idle"
  | "streaming"
  | "completed"
  | "error"
  | "aborted"

export interface ChatNotification {
  id: string
  type: "success" | "error"
  message: string
}

interface ChatState {
  threads: Thread[]
  models: ModelOption[]
  activeThreadId: string | null
  activeConversationKey: string
  messagesByConversation: Record<string, Message[]>
  drafts: Record<string, string>
  streamStatusByConversation: Record<string, StreamStatus>
  modelByConversation: Record<string, string>
  thinkingLevelByConversation: Record<string, ThinkingLevel>
  ragEnabledByConversation: Record<string, boolean>
  notifications: ChatNotification[]
  setThreads: (threads: Thread[]) => void
  setModels: (models: ModelOption[]) => void
  upsertThread: (thread: Thread) => void
  setActiveConversation: (conversationKey: string, threadId: string | null) => void
  setMessages: (conversationKey: string, messages: Message[]) => void
  addMessage: (conversationKey: string, message: Message) => void
  appendMessageContent: (conversationKey: string, messageId: string, content: string) => void
  appendMessageReasoningContent: (
    conversationKey: string,
    messageId: string,
    content: string,
  ) => void
  replaceMessageId: (conversationKey: string, fromId: string, toId: string) => void
  setMessageStatus: (
    conversationKey: string,
    messageId: string,
    status: MessageStatus,
  ) => void
  setMessageStreamPhase: (
    conversationKey: string,
    messageId: string,
    phase: MessageStreamPhase,
  ) => void
  appendMessageAgenticStage: (
    conversationKey: string,
    messageId: string,
    event: AgenticStageEvent,
  ) => void
  setMessageThinkingDuration: (
    conversationKey: string,
    messageId: string,
    durationMs: number,
  ) => void
  setMessageReferences: (
    conversationKey: string,
    messageId: string,
    references: Citation[],
  ) => void
  setDraft: (conversationKey: string, draft: string) => void
  setStreamStatus: (conversationKey: string, status: StreamStatus) => void
  setModel: (conversationKey: string, modelId: string) => void
  setThinkingLevel: (conversationKey: string, thinkingLevel: ThinkingLevel) => void
  setRagEnabled: (conversationKey: string, enabled: boolean) => void
  migrateConversation: (
    fromKey: string,
    toKey: string,
    threadId: string | null,
  ) => void
  removeThread: (threadId: string) => void
  addNotification: (notification: Omit<ChatNotification, "id">) => void
  removeNotification: (notificationId: string) => void
}

export const useChatStore = create<ChatState>((set) => ({
  threads: [],
  models: [DEFAULT_MODEL],
  activeThreadId: null,
  activeConversationKey: NEW_CHAT_KEY,
  messagesByConversation: {},
  drafts: {},
  streamStatusByConversation: {},
  modelByConversation: {},
  thinkingLevelByConversation: {},
  ragEnabledByConversation: {},
  notifications: [],
  setThreads: (threads) => set({ threads }),
  setModels: (models) => set({ models }),
  upsertThread: (thread) =>
    set((state) => ({
      threads: [thread, ...state.threads.filter((item) => item.id !== thread.id)],
    })),
  setActiveConversation: (activeConversationKey, activeThreadId) =>
    set({ activeConversationKey, activeThreadId }),
  setMessages: (conversationKey, messages) =>
    set((state) => ({
      messagesByConversation: {
        ...state.messagesByConversation,
        [conversationKey]: messages,
      },
    })),
  addMessage: (conversationKey, message) =>
    set((state) => ({
      messagesByConversation: {
        ...state.messagesByConversation,
        [conversationKey]: [
          ...(state.messagesByConversation[conversationKey] ?? []),
          message,
        ],
      },
    })),
  appendMessageContent: (conversationKey, messageId, content) =>
    set((state) => ({
      messagesByConversation: {
        ...state.messagesByConversation,
        [conversationKey]: (state.messagesByConversation[conversationKey] ?? []).map(
          (message) =>
            message.id === messageId
              ? { ...message, content: message.content + content }
              : message,
        ),
      },
    })),
  appendMessageReasoningContent: (conversationKey, messageId, content) =>
    set((state) => ({
      messagesByConversation: {
        ...state.messagesByConversation,
        [conversationKey]: (state.messagesByConversation[conversationKey] ?? []).map(
          (message) =>
            message.id === messageId
              ? {
                  ...message,
                  reasoningContent: (message.reasoningContent ?? "") + content,
                }
              : message,
        ),
      },
    })),
  replaceMessageId: (conversationKey, fromId, toId) =>
    set((state) => ({
      messagesByConversation: {
        ...state.messagesByConversation,
        [conversationKey]: (state.messagesByConversation[conversationKey] ?? []).map(
          (message) => (message.id === fromId ? { ...message, id: toId } : message),
        ),
      },
    })),
  setMessageStatus: (conversationKey, messageId, status) =>
    set((state) => ({
      messagesByConversation: {
        ...state.messagesByConversation,
        [conversationKey]: (state.messagesByConversation[conversationKey] ?? []).map(
          (message) => (message.id === messageId ? { ...message, status } : message),
        ),
      },
    })),
  setMessageStreamPhase: (conversationKey, messageId, streamPhase) =>
    set((state) => ({
      messagesByConversation: {
        ...state.messagesByConversation,
        [conversationKey]: (state.messagesByConversation[conversationKey] ?? []).map(
          (message) =>
            message.id === messageId ? { ...message, streamPhase } : message,
        ),
      },
    })),
  appendMessageAgenticStage: (conversationKey, messageId, event) =>
    set((state) => ({
      messagesByConversation: {
        ...state.messagesByConversation,
        [conversationKey]: (state.messagesByConversation[conversationKey] ?? []).map(
          (message) =>
            message.id === messageId
              ? {
                  ...message,
                  agenticStages: [...(message.agenticStages ?? []), event],
                }
              : message,
        ),
      },
    })),
  setMessageThinkingDuration: (conversationKey, messageId, thinkingDurationMs) =>
    set((state) => ({
      messagesByConversation: {
        ...state.messagesByConversation,
        [conversationKey]: (state.messagesByConversation[conversationKey] ?? []).map(
          (message) =>
            message.id === messageId ? { ...message, thinkingDurationMs } : message,
        ),
      },
    })),
  setMessageReferences: (conversationKey, messageId, references) =>
    set((state) => ({
      messagesByConversation: {
        ...state.messagesByConversation,
        [conversationKey]: (state.messagesByConversation[conversationKey] ?? []).map(
          (message) => (message.id === messageId ? { ...message, references } : message),
        ),
      },
    })),
  setDraft: (conversationKey, draft) =>
    set((state) => ({ drafts: { ...state.drafts, [conversationKey]: draft } })),
  setStreamStatus: (conversationKey, status) =>
    set((state) => ({
      streamStatusByConversation: {
        ...state.streamStatusByConversation,
        [conversationKey]: status,
      },
    })),
  setModel: (conversationKey, modelId) =>
    set((state) => ({
      modelByConversation: {
        ...state.modelByConversation,
        [conversationKey]: modelId,
      },
    })),
  setThinkingLevel: (conversationKey, thinkingLevel) =>
    set((state) => ({
      thinkingLevelByConversation: {
        ...state.thinkingLevelByConversation,
        [conversationKey]: thinkingLevel,
      },
    })),
  setRagEnabled: (conversationKey, enabled) =>
    set((state) => ({
      ragEnabledByConversation: {
        ...state.ragEnabledByConversation,
        [conversationKey]: enabled,
      },
    })),
  migrateConversation: (fromKey, toKey, threadId) =>
    set((state) => {
      if (fromKey === toKey) return state

      const messagesByConversation = { ...state.messagesByConversation }
      messagesByConversation[toKey] = messagesByConversation[fromKey] ?? []
      delete messagesByConversation[fromKey]

      const drafts = { ...state.drafts }
      if (fromKey in drafts) {
        drafts[toKey] = drafts[fromKey]
      } else {
        delete drafts[toKey]
      }
      delete drafts[fromKey]

      const streamStatusByConversation = { ...state.streamStatusByConversation }
      streamStatusByConversation[toKey] =
        streamStatusByConversation[fromKey] ?? "idle"
      delete streamStatusByConversation[fromKey]

      const modelByConversation = { ...state.modelByConversation }
      if (fromKey in modelByConversation) {
        modelByConversation[toKey] = modelByConversation[fromKey]
      } else {
        delete modelByConversation[toKey]
      }
      delete modelByConversation[fromKey]

      const thinkingLevelByConversation = { ...state.thinkingLevelByConversation }
      if (fromKey in thinkingLevelByConversation) {
        thinkingLevelByConversation[toKey] = thinkingLevelByConversation[fromKey]
      } else {
        delete thinkingLevelByConversation[toKey]
      }
      delete thinkingLevelByConversation[fromKey]

      const ragEnabledByConversation = { ...state.ragEnabledByConversation }
      if (fromKey in ragEnabledByConversation) {
        ragEnabledByConversation[toKey] = ragEnabledByConversation[fromKey]
      } else {
        delete ragEnabledByConversation[toKey]
      }
      delete ragEnabledByConversation[fromKey]

      const isActiveConversation = state.activeConversationKey === fromKey
      return {
        messagesByConversation,
        drafts,
        streamStatusByConversation,
        modelByConversation,
        thinkingLevelByConversation,
        ragEnabledByConversation,
        ...(isActiveConversation
          ? { activeConversationKey: toKey, activeThreadId: threadId }
          : {}),
      }
    }),
  removeThread: (threadId) =>
    set((state) => {
      const messagesByConversation = { ...state.messagesByConversation }
      const drafts = { ...state.drafts }
      const streamStatusByConversation = { ...state.streamStatusByConversation }
      const modelByConversation = { ...state.modelByConversation }
      const thinkingLevelByConversation = { ...state.thinkingLevelByConversation }
      const ragEnabledByConversation = { ...state.ragEnabledByConversation }

      delete messagesByConversation[threadId]
      delete drafts[threadId]
      delete streamStatusByConversation[threadId]
      delete modelByConversation[threadId]
      delete thinkingLevelByConversation[threadId]
      delete ragEnabledByConversation[threadId]

      return {
        threads: state.threads.filter((thread) => thread.id !== threadId),
        messagesByConversation,
        drafts,
        streamStatusByConversation,
        modelByConversation,
        thinkingLevelByConversation,
        ragEnabledByConversation,
      }
    }),
  addNotification: (notification) =>
    set((state) => ({
      notifications: [
        ...state.notifications,
        { ...notification, id: `notification-${Date.now()}-${Math.random()}` },
      ],
    })),
  removeNotification: (notificationId) =>
    set((state) => ({
      notifications: state.notifications.filter(({ id }) => id !== notificationId),
    })),
}))
