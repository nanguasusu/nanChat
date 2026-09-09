import { create } from "zustand"

import type { Message, MessageStatus, MessageStreamPhase, Thread } from "@/types/chat"

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
  activeThreadId: string | null
  activeConversationKey: string
  messagesByConversation: Record<string, Message[]>
  drafts: Record<string, string>
  streamStatusByConversation: Record<string, StreamStatus>
  notifications: ChatNotification[]
  setThreads: (threads: Thread[]) => void
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
  setMessageThinkingDuration: (
    conversationKey: string,
    messageId: string,
    durationMs: number,
  ) => void
  setDraft: (conversationKey: string, draft: string) => void
  setStreamStatus: (conversationKey: string, status: StreamStatus) => void
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
  activeThreadId: null,
  activeConversationKey: NEW_CHAT_KEY,
  messagesByConversation: {},
  drafts: {},
  streamStatusByConversation: {},
  notifications: [],
  setThreads: (threads) => set({ threads }),
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
  setDraft: (conversationKey, draft) =>
    set((state) => ({ drafts: { ...state.drafts, [conversationKey]: draft } })),
  setStreamStatus: (conversationKey, status) =>
    set((state) => ({
      streamStatusByConversation: {
        ...state.streamStatusByConversation,
        [conversationKey]: status,
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

      const isActiveConversation = state.activeConversationKey === fromKey
      return {
        messagesByConversation,
        drafts,
        streamStatusByConversation,
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

      delete messagesByConversation[threadId]
      delete drafts[threadId]
      delete streamStatusByConversation[threadId]

      return {
        threads: state.threads.filter((thread) => thread.id !== threadId),
        messagesByConversation,
        drafts,
        streamStatusByConversation,
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
