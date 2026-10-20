import { apiRequest } from './client'

export type TaskPriority = 'high' | 'medium' | 'low'
export type TaskFilter = 'all' | 'today' | 'overdue' | 'completed'

export interface Task {
  id: string
  title: string
  notes: string | null
  priority: TaskPriority
  due_at: string | null
  is_completed: boolean
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface TaskList {
  items: Task[]
  total: number
}

export interface TaskDashboard {
  open_count: number
  overdue_count: number
  upcoming: Task[]
}

export interface TaskInput {
  title: string
  notes: string | null
  priority: TaskPriority
  due_at: string | null
}

export function fetchTasks(
  accessToken: string,
  filter: TaskFilter,
  search: string,
): Promise<TaskList> {
  const query = new URLSearchParams({ filter })
  if (search.trim()) query.set('search', search.trim())
  return apiRequest(`/tasks?${query.toString()}`, {}, accessToken)
}

export function fetchTaskDashboard(accessToken: string): Promise<TaskDashboard> {
  return apiRequest('/tasks/dashboard', {}, accessToken)
}

export function createTask(accessToken: string, input: TaskInput): Promise<Task> {
  return apiRequest('/tasks', {
    method: 'POST',
    body: JSON.stringify(input),
  }, accessToken)
}

export function updateTask(
  accessToken: string,
  taskId: string,
  input: Partial<TaskInput> & { is_completed?: boolean },
): Promise<Task> {
  return apiRequest(`/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  }, accessToken)
}

export function deleteTask(accessToken: string, taskId: string): Promise<void> {
  return apiRequest(`/tasks/${taskId}`, { method: 'DELETE' }, accessToken)
}
