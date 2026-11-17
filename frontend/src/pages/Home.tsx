import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import { api, ApiError, type Caderno, type Configuracao } from '../api/client'
import type { OutletCtx } from '../components/Layout'
import { primeiroNome, saudacaoDoDia } from '../lib/format'
import { useAuth } from '../store/auth'

export function Home() {
  const { usuario } = useAuth()
  const { cadernos, recarregarCadernos, setFontesSidebar, modoCriar, setModoCriar } =
    useOutletContext<OutletCtx>()
  const nav = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [cfg, setCfg] = useState<Configuracao | null>(null)
  const [prompt, setPrompt] = useState('')
  const [aviso, setAviso] = useState('')
  const [files, setFiles] = useState<FileList | null>(null)
  const [titulo, setTitulo] = useState('')
  const [erro, setErro] = useState('')
  const [loading, setLoading] = useState(false)

  function abrirSeletorArquivos() {
    setModoCriar(true)
    setAviso('')
    setErro('')
    fileInputRef.current?.click()
  }

  function onArquivosEscolhidos(lista: FileList | null) {
    setFiles(lista)
    if (lista?.length) setModoCriar(true)
  }

  useEffect(() => {
    setFontesSidebar(undefined)
    api.get<Configuracao>('/v1/configuracao').then(setCfg).catch(() => setCfg(null))
  }, [setFontesSidebar])

  async function criar(e: FormEvent) {
    e.preventDefault()
    if (!files?.length) return
    setErro('')
    setLoading(true)
    try {
      const form = new FormData()
      Array.from(files).forEach((f) => form.append('arquivos', f))
      if (titulo.trim()) form.append('titulo', titulo.trim())
      const caderno = await api.postForm<Caderno>('/v1/cadernos', form)
      await recarregarCadernos()
      setModoCriar(false)
      nav(`/cadernos/${caderno.id}`, {
        state: {
          reaproveitado: caderno.do_cache,
          trilhaPronta: true,
          perguntaInicial: prompt.trim() || undefined,
        },
      })
    } catch (err) {
      setErro(err instanceof ApiError || err instanceof Error ? err.message : 'Falha ao criar caderno.')
    } finally {
      setLoading(false)
    }
  }

  function enviarPrompt(e: FormEvent) {
    e.preventDefault()
    const texto = prompt.trim()
    if (!texto) {
      setModoCriar(true)
      setAviso('Envie um PDF ou PPTX para criar o caderno, ou abra um caderno na barra lateral.')
      return
    }
    if (cadernos.length === 0) {
      setModoCriar(true)
      setAviso('Crie um caderno com o material da aula para eu responder com base nele.')
      return
    }
    nav(`/cadernos/${cadernos[0].id}`, { state: { perguntaInicial: texto } })
  }

  const nome = primeiroNome(usuario?.nome || '')

  return (
    <div className="home-centro">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.pptx,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => onArquivosEscolhidos(e.target.files)}
      />
      <div className="hero-icone"><img src="/atitus_icone.png" alt="" /></div>
      <h1 className="saudacao">
        {saudacaoDoDia()}, <span className="grad">{nome}</span>
      </h1>
      <p className="sub">
        Estudo guiado a partir do material da sua aula. Ao enviar o PDF ou PPTX, a Trilha gera
        resumo, mapa mental e quiz de uma vez.
      </p>

      <form className="prompt-box" onSubmit={enviarPrompt}>
        <textarea
          rows={2}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Faça uma pergunta ou crie algo"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              ;(e.currentTarget.form as HTMLFormElement | null)?.requestSubmit()
            }
          }}
        />
        <div className="prompt-acoes">
          <div className="prompt-chips">
            <button className="btn pill" type="button" onClick={abrirSeletorArquivos}>
              + Enviar material
            </button>
            {cadernos[0] && (
              <button className="btn pill" type="button" onClick={() => nav(`/cadernos/${cadernos[0].id}`)}>
                Continuar no último caderno
              </button>
            )}
          </div>
          <button className="btn primary enviar" type="submit" title="Enviar">↑</button>
        </div>
      </form>

      {aviso && !modoCriar && <div className="ok" style={{ width: '100%', marginTop: '1rem' }}>{aviso}</div>}

      {modoCriar && (
        <div className="painel criar-painel">
          <div className="painel-titulo"><span className="ponto" />Novo caderno</div>
          <p className="sub" style={{ fontSize: '0.9rem' }}>
            PDF ou PPTX com texto selecionável · até {cfg?.limites.max_paginas_por_jornada ?? 40} páginas/slides
            e {cfg?.limites.max_tamanho_arquivo_mb ?? 20} MB por arquivo. No envio, a Trilha prepara
            resumo, mapa mental e quiz de uma vez e abre na primeira etapa sugerida.
          </p>
          {aviso && <div className="ok">{aviso}</div>}
          <form onSubmit={criar}>
            <button className="uploader" type="button" onClick={() => fileInputRef.current?.click()}>
              {files?.length
                ? Array.from(files).map((f) => f.name).join(', ')
                : 'Clique para enviar PDF ou PPTX'}
            </button>
            <div className="field" style={{ marginBottom: 0 }}>
              <label htmlFor="nome-caderno">Nome do caderno (opcional)</label>
              <input
                id="nome-caderno"
                value={titulo}
                onChange={(e) => setTitulo(e.target.value)}
                maxLength={80}
                placeholder="Ex.: Aula 03 · Arquitetura de produto"
              />
            </div>
            {erro && <div className="erro">{erro}</div>}
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button className="btn primary" type="submit" disabled={!files?.length || loading} style={{ width: 'auto' }}>
                {loading ? 'Preparando sua jornada…' : 'Criar caderno'}
              </button>
              <button className="btn" type="button" style={{ width: 'auto' }} onClick={() => { setModoCriar(false); setAviso('') }}>
                Cancelar
              </button>
            </div>
          </form>
          {cfg && (
            <p className="aviso" style={{ textAlign: 'left' }}>
              Trilha: <b>offline</b>
              {cfg.usar_api ? <> · Dúvidas: <b>{cfg.modo}</b></> : <> · Dúvidas: <b>offline</b></>}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
