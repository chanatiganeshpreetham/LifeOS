import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useAuth } from '../auth/context'
import {
  addWater,
  completeHabit,
  createHabit,
  createSleepLog,
  fetchHabits,
  fetchMoodHistory,
  fetchSleepLogs,
  fetchTodayMood,
  fetchWaterToday,
  saveMood,
  type Habit,
  type HabitFrequency,
  type HabitWeekday,
  type MoodLog,
  type SleepLog,
  type WaterDay,
} from '../api/healthTracking'
import { dateTimeLocalInZone, dateTimeLocalToIso, formatTaskDue } from '../utils/taskTime'

const moodOptions = [
  { score: 1, emoji: '😞', label: 'Very low' },
  { score: 2, emoji: '🙁', label: 'Low' },
  { score: 3, emoji: '😐', label: 'Okay' },
  { score: 4, emoji: '🙂', label: 'Good' },
  { score: 5, emoji: '😄', label: 'Great' },
]

const weekdayOptions: { value: HabitWeekday; label: string }[] = [
  { value: 'mon', label: 'Mon' },
  { value: 'tue', label: 'Tue' },
  { value: 'wed', label: 'Wed' },
  { value: 'thu', label: 'Thu' },
  { value: 'fri', label: 'Fri' },
  { value: 'sat', label: 'Sat' },
  { value: 'sun', label: 'Sun' },
]

function localDateTime(date: Date, timezone: string): string {
  return dateTimeLocalInZone(date, timezone)
}

type ClockFormat = '24h' | '12h'

function SleepDateTimeInput({
  label,
  value,
  onChange,
  format,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  format: ClockFormat
}) {
  const [date, clock] = value.split('T')
  const [hourText, minuteText] = clock.split(':')
  const hour = Number(hourText)
  const minute = Number(minuteText)
  const displayedHour = format === '24h' ? hourText : String(hour % 12 || 12)
  const period = hour < 12 ? 'am' : 'pm'

  function updateTime(nextHour: number, nextMinute: number, nextPeriod = period) {
    const hour24 = format === '12h'
      ? nextHour % 12 + (nextPeriod === 'pm' ? 12 : 0)
      : nextHour
    onChange(`${date}T${String(hour24).padStart(2, '0')}:${String(nextMinute).padStart(2, '0')}`)
  }

  return (
    <fieldset className="sleep-time-field">
      <legend>{label}</legend>
      <div className="sleep-time-controls">
        <label>
          Date
          <input
            aria-label={`${label} date`}
            onChange={(event) => onChange(`${event.target.value}T${clock}`)}
            required
            type="date"
            value={date}
          />
        </label>
        <label>
          Hour
          <select
            aria-label={`${label} hour`}
            onChange={(event) => updateTime(Number(event.target.value), minute)}
            value={displayedHour}
          >
            {(format === '24h'
              ? Array.from({ length: 24 }, (_, value) => String(value).padStart(2, '0'))
              : Array.from({ length: 12 }, (_, value) => String(value + 1))
            ).map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </label>
        <label>
          Minute
          <select
            aria-label={`${label} minute`}
            onChange={(event) => updateTime(hour, Number(event.target.value))}
            value={String(minute).padStart(2, '0')}
          >
            {Array.from({ length: 60 }, (_, value) => String(value).padStart(2, '0'))
              .map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </label>
        {format === '12h' && (
          <label>
            AM/PM
            <select
              aria-label={`${label} AM or PM`}
              onChange={(event) => updateTime(hour % 12 || 12, minute, event.target.value)}
              value={period}
            >
              <option value="am">AM</option>
              <option value="pm">PM</option>
            </select>
          </label>
        )}
      </div>
    </fieldset>
  )
}

export function HealthPage() {
  const { accessToken, user } = useAuth()
  const timezone = user?.timezone ?? 'Asia/Kolkata'
  const [mood, setMood] = useState<MoodLog | null>(null)
  const [moods, setMoods] = useState<MoodLog[]>([])
  const [historyDays, setHistoryDays] = useState<7 | 30>(7)
  const [sleepLogs, setSleepLogs] = useState<SleepLog[]>([])
  const [habits, setHabits] = useState<Habit[]>([])
  const [water, setWater] = useState<WaterDay | null>(null)
  const [waterAmount, setWaterAmount] = useState('250')
  const [clockFormat, setClockFormat] = useState<ClockFormat>('24h')
  const [frequency, setFrequency] = useState<HabitFrequency>('daily')
  const [busy, setBusy] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [bedtime, setBedtime] = useState(() =>
    localDateTime(new Date(Date.now() - 8 * 60 * 60 * 1000), timezone),
  )
  const [wakeTime, setWakeTime] = useState(() => localDateTime(new Date(), timezone))

  const reload = useCallback(async () => {
    if (!accessToken) return
    const [todayMood, history, sleep, habitList, waterToday] = await Promise.all([
      fetchTodayMood(accessToken),
      fetchMoodHistory(accessToken, historyDays),
      fetchSleepLogs(accessToken, 7),
      fetchHabits(accessToken),
      fetchWaterToday(accessToken),
    ])
    setMood(todayMood)
    setMoods(history.items)
    setSleepLogs(sleep.items)
    setHabits(habitList.items)
    setWater(waterToday)
  }, [accessToken, historyDays])

  useEffect(() => {
    let active = true
    setIsLoading(true)
    setError('')
    reload()
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Could not load health data.')
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [reload])

  async function perform(action: () => Promise<unknown>, message: string) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await action()
      await reload()
      setNotice(message)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save health data.')
    } finally {
      setBusy(false)
    }
  }

  function submitSleep(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken) return
    const form = new FormData(event.currentTarget)
    try {
      const input = {
        bedtime: dateTimeLocalToIso(bedtime, timezone),
        wake_time: dateTimeLocalToIso(wakeTime, timezone),
        quality_rating: Number(form.get('quality_rating')),
      }
      void perform(() => createSleepLog(accessToken, input), 'Sleep log saved.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Enter valid sleep times.')
    }
  }

  function submitWater(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken) return
    const amount = Number(waterAmount)
    if (!Number.isInteger(amount) || amount < 1 || amount > 5000) {
      setError('Enter a whole water amount between 1 and 5,000 ml.')
      return
    }
    void perform(() => addWater(accessToken, amount), `${amount} ml added.`)
  }

  function submitHabit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken) return
    const form = new FormData(event.currentTarget)
    const targetWeekdays = frequency === 'specific_days'
      ? form.getAll('target_weekdays').map(String) as HabitWeekday[]
      : null
    const weeklyCount = Number(form.get('weekly_target_count'))
    const input = {
      name: String(form.get('name') ?? '').trim(),
      colour_hex: '#31805E',
      frequency,
      target_weekdays: targetWeekdays?.length ? targetWeekdays : null,
      weekly_target_count: frequency === 'weekly_count' ? weeklyCount : null,
    }
    void perform(() => createHabit(accessToken, input), 'Habit created.')
    event.currentTarget.reset()
    setFrequency('daily')
  }

  if (isLoading) {
    return <main className="page-content"><p className="welcome-copy">Loading your health space…</p></main>
  }

  const waterPercent = water?.goal_ml ? Math.min(100, water.total_ml / water.goal_ml * 100) : 0

  return (
    <main className="page-content health-page">
      <header className="health-heading">
        <div><p className="eyebrow">Small check-ins, meaningful patterns</p><h1>Health</h1><p className="welcome-copy">A private, non-clinical space for mood, sleep, daily habits and hydration.</p></div>
      </header>
      {error && <p className="form-message form-message-error" role="alert">{error}</p>}
      {notice && <p className="form-message form-message-success" role="status">{notice}</p>}

      <section className="health-feature-card">
        <div className="health-card-heading"><div><p className="eyebrow">A moment for yourself</p><h2>How are you feeling?</h2></div>{mood && <span className="health-today-badge">Today · {moodOptions[mood.mood_score - 1]?.label}</span>}</div>
        <div aria-label="Choose today's mood" className="mood-options" role="group">
          {moodOptions.map((option) => <button
            aria-pressed={mood?.mood_score === option.score}
            className={`mood-option${mood?.mood_score === option.score ? ' is-selected' : ''}`}
            disabled={busy}
            key={option.score}
            onClick={() => accessToken && void perform(() => saveMood(accessToken, option.score), 'Mood check-in saved.')}
            type="button"
          ><span aria-hidden="true">{option.emoji}</span><small>{option.label}</small></button>)}
        </div>
        <div className="health-history-heading"><h3>Mood history</h3><div aria-label="Mood history range" className="health-range-toggle" role="group">
          {[7, 30].map((days) => <button aria-pressed={historyDays === days} key={days} onClick={() => setHistoryDays(days as 7 | 30)} type="button">{days} days</button>)}
        </div></div>
        <div aria-label={`${historyDays}-day mood history`} className={`mood-history mood-history-${historyDays}`}>
          {moods.map((item) => <div className="mood-history-item" key={item.id} title={`${item.log_date}: ${moodOptions[item.mood_score - 1]?.label}`}>
            <div><span style={{ height: `${item.mood_score * 20}%` }} data-score={item.mood_score} /></div>
            <small>{new Date(`${item.log_date}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric' })}</small>
          </div>)}
          {!moods.length && <p className="health-empty">Your mood history will take shape as you check in.</p>}
        </div>
        <p className="health-footnote">Mood check-ins are for personal reflection, not a clinical assessment.</p>
      </section>

      <section className="health-feature-card">
        <div className="health-card-heading"><div><p className="eyebrow">Rest and recovery</p><h2>Log sleep</h2></div></div>
        <form className="health-form health-sleep-form" onSubmit={submitSleep}>
          <fieldset aria-label="Time display format" className="sleep-time-format">
            <legend>Time format</legend>
            <label>
              <input
                checked={clockFormat === '24h'}
                name="time_format"
                onChange={() => setClockFormat('24h')}
                type="radio"
              />
              24-hour
            </label>
            <label>
              <input
                checked={clockFormat === '12h'}
                name="time_format"
                onChange={() => setClockFormat('12h')}
                type="radio"
              />
              12-hour (AM/PM)
            </label>
          </fieldset>
          <SleepDateTimeInput format={clockFormat} label="Bedtime" onChange={setBedtime} value={bedtime} />
          <SleepDateTimeInput format={clockFormat} label="Wake time" onChange={setWakeTime} value={wakeTime} />
          <label>
            Sleep quality
            <select defaultValue="3" name="quality_rating">
              {[1, 2, 3, 4, 5].map((score) => <option key={score} value={score}>{score} / 5</option>)}
            </select>
          </label>
          <button className="primary-button" disabled={busy} type="submit">Save sleep</button>
        </form>
        <div className="health-history-list">
          {sleepLogs.slice(0, 5).map((log) => <article className="health-history-row" key={log.id}>
            <div><strong>{new Date(`${log.sleep_date}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</strong><span>Quality {log.quality_rating}/5 · woke {formatTaskDue(log.wake_time, timezone)}</span></div>
            <strong>{log.duration_hours.toFixed(1)} h</strong>
          </article>)}
          {!sleepLogs.length && <p className="health-empty">Sleep duration is calculated from the bedtime and wake time you enter.</p>}
        </div>
      </section>

      <section className="health-feature-card">
        <div className="health-card-heading"><div><p className="eyebrow">Build a steady rhythm</p><h2>Today's habits</h2></div><span className="health-today-badge">{habits.filter((habit) => habit.completed_today).length} / {habits.length} done</span></div>
        <form className="health-form habit-form" onSubmit={submitHabit}>
          <label>Habit name<input maxLength={150} name="name" placeholder="e.g. Read for 20 minutes" required /></label>
          <label>Schedule<select onChange={(event) => setFrequency(event.target.value as HabitFrequency)} value={frequency}>
            <option value="daily">Every day</option><option value="specific_days">Specific weekdays</option><option value="weekly_count">Times per week</option>
          </select></label>
          {frequency === 'specific_days' && <fieldset className="health-weekdays"><legend>Choose days</legend>{weekdayOptions.map((weekday) => <label key={weekday.value}><input name="target_weekdays" type="checkbox" value={weekday.value} />{weekday.label}</label>)}</fieldset>}
          {frequency === 'weekly_count' && <label>Weekly target<select name="weekly_target_count">{[1, 2, 3, 4, 5, 6, 7].map((count) => <option key={count} value={count}>{count} times per week</option>)}</select></label>}
          <button className="secondary-button" disabled={busy} type="submit">Create habit</button>
        </form>
        <div className="habit-list">
          {habits.map((habit) => <article className="habit-item" key={habit.id}>
            <span aria-hidden="true" className="habit-colour" style={{ backgroundColor: habit.colour_hex }} />
            <div className="habit-details"><strong>{habit.name}</strong><span>{habit.frequency === 'specific_days' ? habit.target_weekdays?.join(', ') : habit.frequency === 'weekly_count' ? `${habit.weekly_completed_count}/${habit.weekly_target_count} this week` : 'Every day'} · Current {habit.current_streak} · Best {habit.longest_streak}</span></div>
            <button aria-label={`Mark ${habit.name} done today`} className={habit.completed_today ? 'habit-complete is-done' : 'habit-complete'} disabled={busy || habit.completed_today} onClick={() => accessToken && void perform(() => completeHabit(accessToken, habit.id), 'Habit marked complete.')} type="button">{habit.completed_today ? 'Done' : 'Complete'}</button>
          </article>)}
          {!habits.length && <p className="health-empty">Add a habit above to begin tracking a routine.</p>}
        </div>
      </section>

      <section className="health-feature-card water-card">
        <div className="health-card-heading"><div><p className="eyebrow">A little more hydration</p><h2>Water today</h2></div><strong className="water-total">{((water?.total_ml ?? 0) / 1000).toFixed(2)} <span>/ {((water?.goal_ml ?? 0) / 1000).toFixed(1)} L</span></strong></div>
        <div aria-label={`${Math.round(waterPercent)} percent of water goal`} className="water-progress"><span style={{ width: `${waterPercent}%` }} /></div>
        <form className="water-add-form" onSubmit={submitWater}>
          <label className="water-amount-control" htmlFor="water-amount">
            Amount (ml)
            <input
              id="water-amount"
              inputMode="numeric"
              max="5000"
              min="1"
              onChange={(event) => setWaterAmount(event.target.value)}
              required
              step="1"
              type="number"
              value={waterAmount}
            />
          </label>
          <button className="primary-button water-add-button" disabled={busy} type="submit">
            ＋ Add {waterAmount ? `${waterAmount} ml` : 'water'}
          </button>
        </form>
        {!!water?.items.length && <p className="health-footnote">Most recent: {water.items.slice(0, 3).map((item) => `${item.amount_ml} ml at ${formatTaskDue(item.logged_at, timezone)}`).join(' · ')}</p>}
      </section>
    </main>
  )
}
