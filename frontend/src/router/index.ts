import { createRouter, createWebHistory } from 'vue-router'

// P0 路由：首页（创建任务）+ 任务页（进度/事件流）；报告阅读页 M1 加入
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
    },
    {
      path: '/research/:id',
      name: 'research',
      component: () => import('../views/ResearchView.vue'),
      props: true,
    },
  ],
})

export default router
