import { useEffect } from "react"
import { CheckCircle2, X, XCircle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useChatStore, type ChatNotification } from "@/stores/chat-store"
import { cn } from "@/lib/utils"

function NotificationItem({ notification }: { notification: ChatNotification }) {
  const removeNotification = useChatStore((state) => state.removeNotification)

  useEffect(() => {
    const timeout = window.setTimeout(() => removeNotification(notification.id), 4500)
    return () => window.clearTimeout(timeout)
  }, [notification.id, removeNotification])

  const isSuccess = notification.type === "success"

  return (
    <div className="flex w-[min(22rem,calc(100vw-2rem))] items-start gap-3 rounded-xl border border-border bg-background p-3 text-sm shadow-lg">
      {isSuccess ? (
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
      ) : (
        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
      )}
      <span className={cn("flex-1 leading-5", isSuccess ? "text-foreground" : "text-red-600 dark:text-red-400")}>
        {notification.message}
      </span>
      <Button aria-label="关闭通知" onClick={() => removeNotification(notification.id)} size="icon" variant="ghost">
        <X className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}

export function NotificationToasts() {
  const notifications = useChatStore((state) => state.notifications)

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {notifications.map((notification) => (
        <div className="pointer-events-auto" key={notification.id}>
          <NotificationItem notification={notification} />
        </div>
      ))}
    </div>
  )
}
