import { useEffect, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { CadernoPage } from './pages/Caderno'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { useAuth } from './store/auth'

function Guard({ children }: { children: ReactNode }) {
  const { usuario, ready } = useAuth()
  if (!ready) return <div className="main login-main"><p className="sub">Carregando…</p></div>
  if (!usuario) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const restaurar = useAuth((s) => s.restaurar)
  useEffect(() => { restaurar() }, [restaurar])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Guard><Layout /></Guard>}>
          <Route index element={<Home />} />
          <Route path="cadernos/:id" element={<CadernoPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
