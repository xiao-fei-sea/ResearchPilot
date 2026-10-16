/**
 * SSE 封装（设计文档 §6.2 / §8.3 api/sse.ts）。
 *
 * 浏览器 EventSource 断线自动重连，但不回传 Last-Event-ID 之外的自定义头——
 * 实际上它会自动带上 Last-Event-ID 头（最后一次收到的 id），后端已支持按它补发缺口。
 * 这里封装：事件回调注册、连接状态回调、手动关闭。
 */
export interface ResearchEvent {
  id: number
  task_id: number
  type: string
  level: string
  stage_run_id: number | null
  payload: Record<string, unknown>
  ts: string
}

export type SseHandler = (event: ResearchEvent) => void

export class ResearchEventStream {
  private es: EventSource | null = null
  private taskUrl: string

  constructor(taskId: number | string) {
    this.taskUrl = `/api/research/${taskId}/events`
  }

  /** 连接并注册回调；返回关闭函数。 */
  open(onEvent: SseHandler, onState?: (connected: boolean) => void): () => void {
    this.es = new EventSource(this.taskUrl)
    this.es.onopen = () => onState?.(true)
    this.es.onerror = () => onState?.(false) // 浏览器将自动重连
    this.es.onmessage = (ev) => {
      try {
        onEvent(JSON.parse(ev.data) as ResearchEvent)
      } catch {
        // 心跳注释帧等非 JSON 数据忽略
      }
    }
    return () => this.close()
  }

  close(): void {
    this.es?.close()
    this.es = null
  }
}
