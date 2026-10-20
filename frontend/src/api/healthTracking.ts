import { apiRequest } from './client'

export interface MoodLog {
  id: string
  mood_score: number
  logged_at: string
  log_date: string
}

export interface SleepLog {
  id: string
  bedtime: string
  wake_time: string
  duration_hours: number
  quality_rating: number
  sleep_date: string
  created_at: string
}

export type HabitFrequency = 'daily' | 'specific_days' | 'weekly_count'
export type HabitWeekday = 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun'

export interface Habit {
  id: string
  name: string
  colour_hex: string
  frequency: HabitFrequency
  target_weekdays: HabitWeekday[] | null
  weekly_target_count: number | null
  current_streak: number
  longest_streak: number
  weekly_completed_count: number
  is_active: boolean
  completed_today: boolean
}

export interface WaterDay {
  log_date: string
  total_ml: number
  goal_ml: number
  items: { id: string; amount_ml: number; logged_at: string }[]
}

export interface WaterLog {
  id: string
  amount_ml: number
  logged_at: string
}

export interface HealthToday {
  date: string
  mood_score: number | null
  water_total_ml: number
  water_goal_ml: number
  habits_completed: number
  habits_total: number
}

export function fetchHealthToday(token: string): Promise<HealthToday> {
  return apiRequest('/health/today', {}, token)
}

export function fetchTodayMood(token: string): Promise<MoodLog | null> {
  return apiRequest('/health/mood', {}, token)
}

export function saveMood(token: string, mood_score: number): Promise<MoodLog> {
  return apiRequest('/health/mood', { method: 'PUT', body: JSON.stringify({ mood_score }) }, token)
}

export function fetchMoodHistory(token: string, days: 7 | 30): Promise<{ items: MoodLog[]; days: number }> {
  return apiRequest(`/health/mood/history?days=${days}`, {}, token)
}

export function fetchSleepLogs(token: string, days = 7): Promise<{ items: SleepLog[] }> {
  return apiRequest(`/health/sleep?days=${days}`, {}, token)
}

export function createSleepLog(
  token: string,
  input: { bedtime: string; wake_time: string; quality_rating: number },
): Promise<SleepLog> {
  return apiRequest('/health/sleep', { method: 'POST', body: JSON.stringify(input) }, token)
}

export function fetchHabits(token: string): Promise<{ items: Habit[]; total: number }> {
  return apiRequest('/health/habits', {}, token)
}

export function createHabit(
  token: string,
  input: {
    name: string
    colour_hex: string
    frequency: HabitFrequency
    target_weekdays: HabitWeekday[] | null
    weekly_target_count: number | null
  },
): Promise<Habit> {
  return apiRequest('/health/habits', { method: 'POST', body: JSON.stringify(input) }, token)
}

export function completeHabit(token: string, habitId: string): Promise<Habit> {
  return apiRequest(`/health/habits/${habitId}/complete`, { method: 'POST' }, token)
}

export function fetchWaterToday(token: string): Promise<WaterDay> {
  return apiRequest('/health/water/today', {}, token)
}

export function addWater(token: string, amount_ml = 250): Promise<WaterLog> {
  return apiRequest('/health/water', { method: 'POST', body: JSON.stringify({ amount_ml }) }, token)
}
