import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { AVISO } from '../lib/format'
import { useAuth } from '../store/auth'

export function Login() {
  const { usuario, login, registrar } = useAuth()
  const nav = useNavigate()
  const [aba, setAba] = useState<'entrar' | 'criar'>('entrar')
  const [erro, setErro] = useState('')
  const [loading, setLoading] = useState(false)
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [senha2, setSenha2] = useState('')

  if (usuario) return <Navigate to="/" replace />

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setErro('')
    setLoading(true)
    try {
      if (aba === 'entrar') {
        await login(email, senha)
      } else {
        if (senha !== senha2) throw new Error('As senhas não coincidem.')
        await registrar(nome, email, senha)
      }
      nav('/')
    } catch (err) {
      setErro(err instanceof ApiError || err instanceof Error ? err.message : 'Falha no login.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="main login-main">
      <div className="logo-wrap" style={{ textAlign: 'center', marginBottom: '1.2rem' }}>
        <img src="/atitus_logo.png" alt="Universidade Atitus" style={{ margin: '0 auto', height: 52 }} />
      </div>
      <div className="painel">
        <h1 className="hero-titulo" style={{ fontSize: '1.8rem', textAlign: 'center' }}>Trilha</h1>
        <p className="sub" style={{ textAlign: 'center', marginBottom: '1.2rem' }}>
          Estudo guiado com tutor inteligente
        </p>
        <div className="tabs">
          <button type="button" className={aba === 'entrar' ? 'active' : ''} onClick={() => setAba('entrar')}>Entrar</button>
          <button type="button" className={aba === 'criar' ? 'active' : ''} onClick={() => setAba('criar')}>Criar conta</button>
        </div>
        <form onSubmit={onSubmit}>
          {aba === 'criar' && (
            <div className="field">
              <label>Nome</label>
              <input value={nome} onChange={(e) => setNome(e.target.value)} required minLength={2} />
            </div>
          )}
          <div className="field">
            <label>E-mail</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="field">
            <label>Senha</label>
            <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required minLength={8} />
          </div>
          {aba === 'criar' && (
            <div className="field">
              <label>Confirmar senha</label>
              <input type="password" value={senha2} onChange={(e) => setSenha2(e.target.value)} required minLength={8} />
            </div>
          )}
          {erro && <div className="erro">{erro}</div>}
          <button className="btn primary" disabled={loading} type="submit">
            {loading ? 'Aguarde…' : aba === 'entrar' ? 'Entrar' : 'Criar conta e entrar'}
          </button>
        </form>
      </div>
      <p className="aviso">{AVISO}</p>
      <p className="aviso">Seus cadernos e histórico ficam salvos na sua conta.</p>
    </div>
  )
}
