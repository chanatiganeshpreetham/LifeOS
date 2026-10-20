import { apiRequest } from './client'

export type ReminderFrequency = 'daily' | 'weekly' | 'monthly' | 'custom'
export type ReminderWeekday = 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun'

export interface Reminder {
  id: string
  title: string
  notes: string | null
  remind_at: string
  is_recurring: boolean
  frequency: ReminderFrequency | null
  interval_days: number | null
  weekdays: ReminderWeekday[] | null
  is_active: boolean
  is_acknowledged: boolean
  created_at: string
  updated_at: string
}

export interface ReminderInput {
  title: string
  notes: string | null
  remind_at: string
  is_recurring: boolean
  frequency: ReminderFrequency | null
  interval_days: number | null
  weekdays: ReminderWeekday[] | null
}

export interface Notification {
  id: string
  reminder_id: string | null
  payload_summary: string | null
  sent_at: string
  read_at: string | null
}

export interface NotificationList {
  items: Notification[]
  unread_count: number
}

export function fetchReminders(accessToken: string): Promise<{ items: Reminder[]; total: number }> {
  return apiRequest('/reminders', {}, accessToken)
}

export function fetchDashboardReminders(
  accessToken: string,
): Promise<{ items: Reminder[]; total: number }> {
  return apiRequest('/reminders/dashboard', {}, accessToken)
}

export function createReminder(accessToken: string, input: ReminderInput): Promise<Reminder> {
  return apiRequest('/reminders', { method: 'POST', body: JSON.stringify(input) }, accessToken)
}

export function updateReminder(
  accessToken: string,
  reminderId: string,
  input: Partial<ReminderInput> & { is_active?: boolean },
): Promise<Reminder> {
  return apiRequest(`/reminders/${reminderId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  }, accessToken)
}

export function acknowledgeReminder(accessToken: string, reminderId: string): Promise<Reminder> {
  return apiRequest(`/reminders/${reminderId}/acknowledge`, { method: 'POST' }, accessToken)
}

export function deleteReminder(accessToken: string, reminderId: string): Promise<void> {
  return apiRequest(`/reminders/${reminderId}`, { method: 'DELETE' }, accessToken)
}

export function fetchNotifications(accessToken: string): Promise<NotificationList> {
  return apiRequest('/notifications?limit=30', {}, accessToken)
}

export function markNotificationRead(accessToken: string, id: string): Promise<Notification> {
  return apiRequest(`/notifications/${id}/read`, { method: 'POST' }, accessToken)
}

export function markAllNotificationsRead(accessToken: string): Promise<{ message: string }> {
  return apiRequest('/notifications/read-all', { method: 'POST' }, accessToken)
}

export function fetchPushConfig(accessToken: string): Promise<{ enabled: boolean; public_key: string | null }> {
  return apiRequest('/push/config', {}, accessToken)
}

export function registerPushSubscription(
  accessToken: string,
  input: { endpoint: string; p256dh_key: string; auth_key: string; device_label: string },
): Promise<void> {
  return apiRequest('/push/subscription', { method: 'PUT', body: JSON.stringify(input) }, accessToken)
}

export function removePushSubscription(accessToken: string, endpoint: string): Promise<{ message: string }> {
  const query = new URLSearchParams({ endpoint })
  return apiRequest(`/push/subscription?${query}`, { method: 'DELETE' }, accessToken)
}
