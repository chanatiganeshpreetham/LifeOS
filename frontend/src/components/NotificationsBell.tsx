import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchNotifications, markAllNotificationsRead, markNotificationRead, type Notification } from '../api/reminders'
import { useAuth } from '../auth/context'

export function NotificationsBell() {
  const { accessToken } = useAuth()
  const [items, setItems] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [isOpen, setIsOpen] = useState(false)
  const [error, setError] = useState('')
  const [isUpdating, setIsUpdating] = useState(false)

  const refresh = useCallback(async () => {
    if (!accessToken) return
    try {
      const response = await fetchNotifications(accessToken)
      setItems(response.items)
      setUnreadCount(response.unread_count)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load notifications.')
    }
  }, [accessToken])

  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => void refresh(), 30_000)
    return () => window.clearInterval(timer)
  }, [refresh])

  async function markRead(notification: Notification) {
    if (!accessToken || notification.read_at) return
    setIsUpdating(true)
    setError('')
    try {
      await markNotificationRead(accessToken, notification.id)
      await refresh()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not mark the notification as read.')
    } finally {
      setIsUpdating(false)
    }
  }

  async function markAllRead() {
    if (!accessToken || unreadCount === 0) return
    setIsUpdating(true)
    setError('')
    try {
      await markAllNotificationsRead(accessToken)
      await refresh()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not mark notifications as read.')
    } finally {
      setIsUpdating(false)
    }
  }

  return (
    <div className="notification-menu">
      <button
        aria-expanded={isOpen}
        aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ''}`}
        className="notification-bell"
        onClick={() => setIsOpen((open) => !open)}
        type="button"
      >
        <span aria-hidden="true">♢</span>
        {unreadCount > 0 && <span className="notification-count">{unreadCount > 99 ? '99+' : unreadCount}</span>}
      </button>
      {isOpen && (
        <section aria-label="Notifications" className="notification-popover">
          <div className="notification-popover-heading">
            <strong>Notifications</strong>
            <button className="text-button" disabled={isUpdating || unreadCount === 0} onClick={() => void markAllRead()} type="button">
              Mark all read
            </button>
          </div>
          {error && <p className="notification-error" role="alert">{error}</p>}
          {items.length === 0 ? (
            <p className="notification-empty">You’re all caught up.</p>
          ) : (
            <ul className="notification-list">
              {items.slice(0, 8).map((item) => (
                <li className={`notification-item${item.read_at ? ' is-read' : ''}`} key={item.id}>
                  <button disabled={isUpdating} onClick={() => void markRead(item)} type="button">
                    <span>{item.payload_summary ?? 'A reminder is due.'}</span>
                    <time dateTime={item.sent_at}>{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(item.sent_at))}</time>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <Link className="notification-view-all" onClick={() => setIsOpen(false)} to="/reminders">
            View reminders
          </Link>
        </section>
      )}
    </div>
  )
}
