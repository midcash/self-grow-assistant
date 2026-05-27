import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: () => import('@/views/Dashboard.vue') },
    { path: '/qualities', name: 'qualities', component: () => import('@/views/Qualities.vue') },
    { path: '/input', name: 'input', component: () => import('@/views/DailyInput.vue') },
    { path: '/checkin', name: 'checkin', component: () => import('@/views/CheckIn.vue') },
    { path: '/report', name: 'report', component: () => import('@/views/Report.vue') },
    { path: '/role-models', name: 'roleModels', component: () => import('@/views/RoleModels.vue') },
  ],
})

export default router
