import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
  { path: '/', name: 'projects', component: () => import('../views/Projects.vue') },
  { path: '/organize', name: 'organize', component: () => import('../views/Organize.vue') },
  { path: '/projects/:id', name: 'project-detail', component: () => import('../views/ProjectDetail.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) return '/login'
  if (to.path === '/login' && token) return '/'
})

export default router
