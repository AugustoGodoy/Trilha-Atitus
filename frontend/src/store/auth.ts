import { create } from 'zustand'
import { api, getToken, setToken, type Usuario } from '../api/client'

type AuthState = {
  usuario: Usuario | null
  ready: boolean
  restaurar: () => Promise<void>
  login: (email: string, senha: string) => Promise<void>
  registrar: (nome: string, email: string, senha: string) => Promise<void>
  sair: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  usuario: null,
  ready: false,
  async restaurar() {
    const token = getToken()
    if (!token) {
      set({ usuario: null, ready: true })
      return
    }
    try {
      const usuario = await api.get<Usuario>('/v1/sessoes/atual')
      set({ usuario, ready: true })
    } catch {
      setToken(null)
      set({ usuario: null, ready: true })
    }
  },
  async login(email, senha) {
    const data = await api.post<{ token: string; usuario: Usuario }>('/v1/sessoes', { email, senha })
    setToken(data.token)
    set({ usuario: data.usuario })
  },
  async registrar(nome, email, senha) {
    await api.post('/v1/usuarios', { nome, email, senha })
    const data = await api.post<{ token: string; usuario: Usuario }>('/v1/sessoes', { email, senha })
    setToken(data.token)
    set({ usuario: data.usuario })
  },
  async sair() {
    try { await api.del('/v1/sessoes/atual') } catch { /* ignore */ }
    setToken(null)
    set({ usuario: null })
  },
}))
