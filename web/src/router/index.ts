import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
    },
    {
      path: '/',
      component: MainLayout,
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/Dashboard.vue'),
          meta: { title: '数据看板', icon: 'DataBoard' },
        },
        {
          path: 'devices',
          name: 'Devices',
          component: () => import('@/views/DeviceManage.vue'),
          meta: { title: '设备管理', icon: 'Monitor' },
        },
        {
          path: 'tasks',
          name: 'Tasks',
          component: () => import('@/views/TaskManage.vue'),
          meta: { title: '任务管理', icon: 'List' },
        },
        {
          path: 'audio',
          name: 'Audio',
          component: () => import('@/views/AudioList.vue'),
          meta: { title: '音频列表', icon: 'Headset' },
        },
        {
          path: 'audio/:id',
          name: 'AudioDetail',
          component: () => import('@/views/AudioDetail.vue'),
          meta: { title: '音频详情', hidden: true },
        },
        {
          path: 'realtime',
          name: 'Realtime',
          component: () => import('@/views/RealtimeMonitor.vue'),
          meta: { title: '实时监控', icon: 'VideoCamera' },
        },
        {
          path: 'speakers',
          name: 'Speakers',
          component: () => import('@/views/SpeakerManage.vue'),
          meta: { title: '说话人库', icon: 'User' },
        },
        {
          path: 'search',
          name: 'Search',
          component: () => import('@/views/Search.vue'),
          meta: { title: '全文检索', icon: 'Search' },
        },
        {
          path: 'alerts',
          name: 'Alerts',
          component: () => import('@/views/AlertConfig.vue'),
          meta: { title: '告警配置', icon: 'Bell' },
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/SystemSettings.vue'),
          meta: { title: '系统设置', icon: 'Setting' },
        },
      ],
    },
  ],
})

// Navigation guard
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
