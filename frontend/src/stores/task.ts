/**
 * 任务 store（设计文档 §8.2 状态管理）。
 * 管理任务列表、当前任务与 SSE 事件流；P0 阶段事件仅展示到时间线。
 */
import { defineStore } from 'pinia'

import { researchApi, type TaskOut } from '../api/client'
import { ResearchEventStream, type ResearchEvent } from '../api/sse'

export const useTaskStore = defineStore('task', {
  state: () => ({
    tasks: [] as TaskOut[],
    total: 0,
    current: null as TaskOut | null,
    events: [] as ResearchEvent[],
    connected: false,
    _closeFn: null as null | (() => void),
  }),
  actions: {
    async fetchTasks() {
      const { data } = await researchApi.list()
      this.tasks = data.items
      this.total = data.total
    },
    async create(topic: string) {
      const { data } = await researchApi.create(topic)
      await this.fetchTasks()
      return data.task_id
    },
    async openTask(taskId: number | string) {
      this.closeStream()
      const { data } = await researchApi.get(taskId)
      this.current = data
      this.events = []
      const stream = new ResearchEventStream(taskId)
      this._closeFn = stream.open(
        (event) => {
          this.events.push(event)
          // done/error 事件携带最终状态，直接刷新任务详情
          if (event.type === 'done' || event.type === 'error') {
            researchApi.get(taskId).then(({ data }) => (this.current = data))
          }
        },
        (connected) => (this.connected = connected),
      )
    },
    closeStream() {
      this._closeFn?.()
      this._closeFn = null
      this.connected = false
    },
  },
})
