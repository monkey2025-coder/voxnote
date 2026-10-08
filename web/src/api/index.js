import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const api = axios.create({ baseURL: '/', timeout: 30000 })

// 请求拦截:自动带上 JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截:统一错误提示,401 跳登录
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail || err.message
    if (status === 401) {
      localStorage.removeItem('token')
      router.push('/login')
      ElMessage.error('登录已过期,请重新登录')
    } else {
      ElMessage.error(typeof detail === 'string' ? detail : '请求失败')
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  register: (username, password) => api.post('/auth/register', { username, password }),
  login: (username, password) => api.post('/auth/login', { username, password }),
  me: () => api.get('/auth/me'),
}

export const projectApi = {
  list: () => api.get('/projects'),
  create: (name) => api.post('/projects', { name }),
  update: (id, name) => api.put(`/projects/${id}`, { name }),
  remove: (id) => api.delete(`/projects/${id}`),
  notes: (id) => api.get(`/projects/${id}/notes`),
}

export const noteApi = {
  inbox: () => api.get('/notes/inbox'),
  update: (id, data) => api.put(`/notes/${id}`, data),
  remove: (id) => api.delete(`/notes/${id}`),
}

export const annotationApi = {
  addText: (noteId, content) => {
    const form = new FormData()
    form.append('type', 'text')
    form.append('content', content)
    return api.post(`/notes/${noteId}/annotations`, form)
  },
  addImage: (noteId, file) => {
    const form = new FormData()
    form.append('type', 'image')
    form.append('file', file)
    return api.post(`/notes/${noteId}/annotations`, form)
  },
  remove: (id) => api.delete(`/annotations/${id}`),
}

// 给 /files/... 的 URL 追加 token 查询参数(<audio>/<img> 标签无法带 header)
export function withToken(url) {
  if (!url) return url
  const token = localStorage.getItem('token')
  if (!token) return url
  return `${url}${url.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`
}

export default api
