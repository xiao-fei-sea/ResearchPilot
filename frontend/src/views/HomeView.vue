<script setup lang="ts">
// 首页：主题输入 + 创建任务 + 历史任务列表（设计文档 §8.1）
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useTaskStore } from '../stores/task'

const store = useTaskStore()
const router = useRouter()
const topic = ref('')
const creating = ref(false)

const STATUS_TAG: Record<string, 'info' | 'primary' | 'success' | 'warning' | 'danger'> = {
  pending: 'info',
  done: 'success',
  failed: 'danger',
  cancelled: 'warning',
}

async function submit() {
  if (topic.value.trim().length < 2) {
    ElMessage.warning('请输入研究主题（至少 2 个字符）')
    return
  }
  creating.value = true
  try {
    const taskId = await store.create(topic.value.trim())
    ElMessage.success('任务已创建')
    router.push(`/research/${taskId}`)
  } catch (e) {
    ElMessage.error(`创建失败：${(e as Error).message}`)
  } finally {
    creating.value = false
  }
}

onMounted(() => store.fetchTasks())
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-8 pt-8">
    <section class="space-y-3">
      <h1 class="text-xl font-semibold">发起一项研究</h1>
      <el-input
        v-model="topic"
        type="textarea"
        :rows="3"
        placeholder="例如：调研 2025–2026 年 AI Agent 在软件工程中的应用，比较主流开源项目的架构、优缺点和发展趋势。"
      />
      <div class="text-right">
        <el-button type="primary" :loading="creating" @click="submit">开始研究</el-button>
      </div>
    </section>

    <section class="space-y-3">
      <h2 class="text-base font-semibold">历史任务</h2>
      <el-table :data="store.tasks" @row-click="(row: any) => router.push(`/research/${row.id}`)">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="topic" label="主题" min-width="300" show-overflow-tooltip />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="STATUS_TAG[row.status] ?? 'primary'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>
