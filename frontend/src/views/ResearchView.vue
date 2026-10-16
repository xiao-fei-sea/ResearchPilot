<script setup lang="ts">
// 任务页 P0 简版：任务状态卡 + SSE 实时事件流。
// M1/M2 演进为三栏布局（时间线 / 报告阅读 / 来源面板，见设计文档 §8.1）。
import { computed, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

import { useTaskStore } from '../stores/task'

const route = useRoute()
const store = useTaskStore()

const taskId = route.params.id as string
store.openTask(taskId)
onUnmounted(() => store.closeStream())

const STATUS_TAG: Record<string, 'info' | 'primary' | 'success' | 'warning' | 'danger'> = {
  pending: 'info',
  done: 'success',
  failed: 'danger',
  cancelled: 'warning',
}

const LEVEL_TAG: Record<string, 'info' | 'warning' | 'danger'> = {
  info: 'info',
  progress: 'info',
  warn: 'warning',
  error: 'danger',
}

const running = computed(
  () =>
    store.current &&
    !['done', 'failed', 'cancelled'].includes(store.current.status),
)

async function refresh() {
  await store.openTask(taskId)
}
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6 pt-6">
    <section v-if="store.current" class="space-y-2">
      <div class="flex items-center gap-3">
        <h1 class="text-lg font-semibold">任务 #{{ store.current.id }}</h1>
        <el-tag :type="STATUS_TAG[store.current.status] ?? 'primary'">
          {{ store.current.status }}
        </el-tag>
        <el-tag v-if="store.connected" type="success" effect="plain" size="small">
          实时连接中
        </el-tag>
        <el-button v-if="!running" size="small" text type="primary" @click="refresh">
          刷新
        </el-button>
      </div>
      <p class="text-gray-600">{{ store.current.topic }}</p>
      <div v-if="store.current.stats && Object.keys(store.current.stats).length" class="flex flex-wrap gap-3 text-sm">
        <el-tag
          v-for="(v, k) in store.current.stats"
          :key="k"
          type="info"
          effect="plain"
        >
          {{ k }}: {{ v }}
        </el-tag>
      </div>
    </section>

    <section class="space-y-2">
      <h2 class="text-base font-semibold">执行事件流</h2>
      <el-empty v-if="!store.events.length" description="等待事件…" />
      <el-timeline v-else>
        <el-timeline-item
          v-for="e in store.events"
          :key="e.id"
          :timestamp="e.ts"
          :type="LEVEL_TAG[e.level] ?? 'primary'"
        >
          <span class="font-mono text-xs text-gray-400">{{ e.type }}</span>
          <span class="ml-2">{{ (e.payload as any).message }}</span>
        </el-timeline-item>
      </el-timeline>
    </section>
  </div>
</template>
