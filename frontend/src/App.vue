<script setup lang="ts">
// 全局布局壳（P0 极简：顶栏 + 路由出口）
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const showBack = computed(() => route.name === 'research')
</script>

<template>
  <el-container class="h-full">
    <el-header class="flex items-center gap-3 border-b border-gray-200">
      <span class="text-lg font-bold tracking-wide">ResearchPilot</span>
      <span class="text-sm text-gray-400">多源检索与研究报告生成平台</span>
      <router-link v-if="showBack" to="/" class="ml-auto text-sm text-blue-500">
        ← 返回首页
      </router-link>
    </el-header>
    <el-main class="bg-gray-50">
      <router-view />
    </el-main>
  </el-container>
</template>
