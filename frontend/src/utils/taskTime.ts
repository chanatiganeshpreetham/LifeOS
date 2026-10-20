function dateTimeParts(date: Date, timeZone: string): Record<string, string> {
  return Object.fromEntries(
    new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    })
      .formatToParts(date)
      .filter((part) => part.type !== 'literal')
      .map(({ type, value }) => [type, value]),
  )
}

export function dateTimeLocalInZone(date: Date, timeZone: string): string {
  const parts = dateTimeParts(date, timeZone)
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`
}

export function dateTimeLocalToIso(value: string, timeZone: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value)
  if (!match) throw new Error('Enter a valid due date and time.')
  const [, yearText, monthText, dayText, hourText, minuteText] = match
  const desiredUtc = Date.UTC(
    Number(yearText),
    Number(monthText) - 1,
    Number(dayText),
    Number(hourText),
    Number(minuteText),
  )
  let timestamp = desiredUtc
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const parts = dateTimeParts(new Date(timestamp), timeZone)
    const representedUtc = Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day),
      Number(parts.hour),
      Number(parts.minute),
    )
    timestamp += desiredUtc - representedUtc
  }
  const result = new Date(timestamp)
  if (dateTimeLocalInZone(result, timeZone) !== value) {
    throw new Error('That local time does not exist in your profile timezone.')
  }
  return result.toISOString()
}

export function formatTaskDue(value: string, timeZone: string): string {
  return new Intl.DateTimeFormat(undefined, {
    timeZone,
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function overdueDays(value: string, timeZone: string): number {
  const dueDate = dateTimeParts(new Date(value), timeZone)
  const today = dateTimeParts(new Date(), timeZone)
  const dueDay = Date.UTC(Number(dueDate.year), Number(dueDate.month) - 1, Number(dueDate.day))
  const todayDay = Date.UTC(Number(today.year), Number(today.month) - 1, Number(today.day))
  return Math.max(0, Math.floor((todayDay - dueDay) / 86_400_000))
}
