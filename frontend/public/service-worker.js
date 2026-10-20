self.addEventListener('push', (event) => {
  let payload = {}
  try {
    payload = event.data ? event.data.json() : {}
  } catch {
    payload = { body: event.data?.text() ?? 'You have a reminder.' }
  }

  event.waitUntil(
    self.registration.showNotification(payload.title ?? 'LifeOS reminder', {
      body: payload.body ?? 'You have a reminder.',
      icon: '/lifeos-notification.svg',
      badge: '/lifeos-notification.svg',
      data: { url: payload.url ?? '/reminders' },
      tag: payload.tag,
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const destination = new URL(event.notification.data?.url ?? '/reminders', self.location.origin)
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      const existing = clients.find((client) => new URL(client.url).origin === destination.origin)
      if (existing) {
        existing.navigate(destination.href)
        return existing.focus()
      }
      return self.clients.openWindow(destination.href)
    }),
  )
})
