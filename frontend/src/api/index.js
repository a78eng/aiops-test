import axios from 'axios'

// 统一 API 实例：开发走 Vite 代理，生产走 Nginx 转发，前端代码无需区分
const api = axios.create({
  baseURL: '/api',
  timeout: 300000    // 大模型生成较慢，超时放宽到 120 秒
})

// 请求拦截器：自动携带 JWT token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截器：统一处理 401（token 过期）跳登录页
api.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
