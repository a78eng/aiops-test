import { createRouter, createWebHistory } from 'vue-router'
const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '监控仪表盘' } },
  { path: '/report', name: 'Analysis', component: () => import('../views/Analysis.vue'), meta: { title: '智能分析中心' } },
  { path: '/sop', name: 'SopKnowledge', component: () => import('../views/SopKnowledge.vue'), meta: { title: 'SOP 知识库' } },
  { path: '/rag', name: 'RagChat', component: () => import('../views/RagChat.vue'), meta: { title: 'AI 知识问答' } },
  { path: '/work', name: 'WorkCenter', component: () => import('../views/WorkCenter.vue'), meta: { title: '处理中心' } },
  { path: '/scripts', name: 'Scripts', component: () => import('../views/Scripts.vue'), meta: { title: '脚本模板' } },
  { path: '/team', name: 'Team', component: () => import('../views/Team.vue'), meta: { title: '团队管理', admin: true } }
]
const router = createRouter({ history: createWebHistory(), routes })
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) return next('/login')
  if (to.meta.admin && localStorage.getItem('role') !== 'admin') return next('/dashboard')
  next()
})
export default router
