import {
  LoaderCircle,
  MessageSquarePlus,
  Moon,
  Settings,
  Sun,
  Trash2,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import type { StreamStatus } from "@/stores/chat-store"
import type { Thread } from "@/types/chat"

interface SidebarProps {
  activeThreadId: string | null
  isDark: boolean
  isOpen: boolean
  streamStatusByConversation: Record<string, StreamStatus>
  threads: Thread[]
  onDeleteThread: (thread: Thread) => void
  onNewChat: () => void
  onSelectThread: (threadId: string) => void
  onOpenSettings: () => void
  onToggleTheme: () => void
}

export function Sidebar({
  activeThreadId,
  isDark,
  isOpen,
  streamStatusByConversation,
  threads,
  onDeleteThread,
  onNewChat,
  onOpenSettings,
  onSelectThread,
  onToggleTheme,
}: SidebarProps) {
  return (
    <aside
      aria-hidden={!isOpen}
      className={`fixed inset-y-0 left-0 z-40 flex w-72 shrink-0 flex-col overflow-hidden bg-sidebar shadow-xl transition-[width,transform,opacity] duration-200 md:relative md:inset-auto md:z-auto md:h-full md:min-h-0 md:shadow-none ${
        isOpen
          ? "translate-x-0 border-r border-border md:w-64"
          : "-translate-x-full pointer-events-none border-r-0 opacity-0 md:w-0"
      }`}
      id="chat-sidebar"
    >
      <div className="flex h-14 shrink-0 items-center px-5">
        <div className="px-2 text-sm font-semibold tracking-tight">AI Chat</div>
      </div>

      <div className="px-3 pb-3">
        <Button className="w-full justify-start" onClick={onNewChat} variant="outline">
          <MessageSquarePlus className="h-4 w-4" />
          New chat
        </Button>
      </div>

      <div className="block flex-1 overflow-y-auto px-3">
        <p className="px-2 pb-2 pt-3 text-xs font-medium text-muted-foreground">Recent</p>
        <div className="space-y-1">
          {threads.length === 0 && (
            <p className="px-2 py-2 text-xs text-muted-foreground">暂无会话</p>
          )}
          {threads.map((thread) => (
            <div
              className={`group flex min-w-0 items-center rounded-md text-sm transition-colors ${
                activeThreadId === thread.id
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground"
              }`}
              key={thread.id}
            >
              <button
                className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-2 text-left hover:text-foreground"
                onClick={() => onSelectThread(thread.id)}
                type="button"
              >
                <span className="min-w-0 flex-1 truncate">{thread.title}</span>
                {streamStatusByConversation[thread.id] === "streaming" && (
                  <LoaderCircle className="h-3.5 w-3.5 shrink-0 animate-spin" />
                )}
              </button>
              <Button
                aria-label={`删除会话：${thread.title}`}
                className="mr-1 h-7 w-7 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 hover:text-destructive"
                disabled={streamStatusByConversation[thread.id] === "streaming"}
                onClick={() => onDeleteThread(thread)}
                size="icon"
                variant="ghost"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-border px-3 py-3">
        <div className="flex items-center gap-2 px-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-medium">Y</div>
          <span className="text-sm text-muted-foreground">Workspace</span>
        </div>
        <div className="flex items-center gap-1">
          <Button aria-label="打开设置" onClick={onOpenSettings} size="icon" variant="ghost">
            <Settings className="h-4 w-4" />
          </Button>
          <Button aria-label={isDark ? "切换到亮色主题" : "切换到暗色主题"} onClick={onToggleTheme} size="icon" variant="ghost">
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </aside>
  )
}
