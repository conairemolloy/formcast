import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

export function setAuthToken(token) {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    localStorage.setItem('auth_token', token)
  }
}

export function clearAuthToken() {
  delete api.defaults.headers.common['Authorization']
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_user')
}

const stored = localStorage.getItem('auth_token')
if (stored) {
  api.defaults.headers.common['Authorization'] = `Bearer ${stored}`
}

export default api
