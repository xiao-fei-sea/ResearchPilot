/**
 * axios 封装（设计文档 §8.3 api/client.ts）。
 * 开发期走 Vite 代理（/api → localhost:8000），生产期同域由 Nginx 反代。
 */
import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  timeout: 30_000,
})

// ---- 类型（与后端 app/schemas/task.py 对应）----
export interface TaskOut {
  id: number
  topic: string
  status: string
  params: Record<string, unknown>
  budget: Record<string, unknown>
  stats: Record<string, unknown>
  created_at: string
}

export interface TaskListOut {
  items: TaskOut[]
  total: number
}

// ---- 任务接口 ----
export const researchApi = {
  create(topic: string, params: Record<string, unknown> = {}) {
    return api.post<{ task_id: number; status: string }>('/research', { topic, params })
  },
  list(limit = 20, offset = 0) {
    return api.get<TaskListOut>('/research', { params: { limit, offset } })
  },
  get(taskId: number | string) {
    return api.get<TaskOut>(`/research/${taskId}`)
  },
  cancel(taskId: number | string) {
    return api.post(`/research/${taskId}/cancel`)
  },
}
