import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useLocation, useNavigate, useOutletContext, useParams } from 'react-router-dom'
import { instance } from '@viz-js/viz'
import { api, apiUrl, ApiError, type Caderno, type Configuracao } from '../api/client'
import type { OutletCtx } from '../components/Layout'
import { dataCurta, negritoHtml, primeiroNome } from '../lib/format'
import { useAuth } from '../store/auth'

type View = 'chat' | 'resumo' | 'mapa' | 'quiz'
type Mensagem = { pergunta: string; resposta: string; fontes: { arquivo: string; pagina: number }[]; sem_base?: boolean }
type Mapa = { nos: { id: string; rotulo: string; fonte: { arquivo: string; pagina: number } }[]; relacoes: { de: string; para: string; tipo: string }[] }

/** Ordem sugerida da trilha (do simples ao profundo). */
const VISOES: { key: View; label: string }[] = [
  { key: 'resumo', label: 'Resumo' },
  { key: 'mapa', label: 'Mapa mental' },
  { key: 'quiz', label: 'Quiz' },
  { key: 'chat', label: 'Dúvidas' },
]

const ORDEM_TRILHA: View[] = VISOES.map((v) => v.key)

function Citacao({ fonte }: { fonte: { arquivo: string; pagina: number } }) {
  return <span className="cit">📄 {fonte.arquivo} · <b>p. {fonte.pagina}</b></span>
}

export function CadernoPage() {
  const { id } = useParams()
  const cadernoId = Number(id)
  const { usuario } = useAuth()
  const { setFontesSidebar, recarregarCadernos } = useOutletContext<OutletCtx>()
  const nav = useNavigate()
  const location = useLocation()
  const [caderno, setCaderno] = useState<Caderno | null>(null)
  const estadoNav = location.state as { reaproveitado?: boolean; perguntaInicial?: string; trilhaPronta?: boolean } | null
  const iniciaNoChat = Boolean(estadoNav?.perguntaInicial?.trim())
  const [view, setView] = useState<View>(iniciaNoChat ? 'chat' : 'resumo')
  const [cfg, setCfg] = useState<Configuracao | null>(null)
  const [erro, setErro] = useState('')
  const [reaproveitado, setReaproveitado] = useState(Boolean(estadoNav?.reaproveitado))
  const [bannerTrilha, setBannerTrilha] = useState(
    Boolean(estadoNav?.trilhaPronta) || (Boolean(estadoNav?.reaproveitado) && !estadoNav?.perguntaInicial),
  )
  const [perguntaPendente, setPerguntaPendente] = useState(estadoNav?.perguntaInicial?.trim() || '')
  /** Etapas já concluídas — só libera a próxima depois de concluir a atual. */
  const [concluidos, setConcluidos] = useState<Set<View>>(() =>
    iniciaNoChat ? new Set<View>(['resumo', 'mapa', 'quiz']) : new Set(),
  )
  const [modoFoco, setModoFoco] = useState(
    Boolean(estadoNav?.trilhaPronta) || (Boolean(estadoNav?.reaproveitado) && !iniciaNoChat),
  )

  const [mensagens, setMensagens] = useState<Mensagem[]>([])
  const [sugestoes, setSugestoes] = useState<string[]>([])
  const [pergunta, setPergunta] = useState('')
  const [perguntando, setPerguntando] = useState(false)
  const [prontoChat, setProntoChat] = useState(false)

  const [resumo, setResumo] = useState<{ topicos: { titulo: string; texto_destacado: string; fonte: { arquivo: string; pagina: number } }[]; termos: { termo: string; definicao: string }[] } | null>(null)
  const [mapa, setMapa] = useState<Mapa | null>(null)
  const [dot, setDot] = useState('')
  const [svg, setSvg] = useState('')
  const [noSel, setNoSel] = useState('')
  const [trecho, setTrecho] = useState<{ texto: string; imagens: string[] } | null>(null)
  const [novoNo, setNovoNo] = useState('')
  const [paiNo, setPaiNo] = useState('')

  const [quiz, setQuiz] = useState<{ questoes: { enunciado: string; alternativas: string[]; gabarito: string; justificativa: string; fonte: { arquivo: string; pagina: number }; nivel: string }[] } | null>(null)
  const [resultados, setResultados] = useState<{ nota: number }[]>([])
  const [respostas, setRespostas] = useState<Record<number, string>>({})
  const [corrigido, setCorrigido] = useState<{
    nota: number; acertos: number; total: number
    itens: { indice: number; acertou: boolean; marcada: string | null; gabarito: string; justificativa: string; fonte: { arquivo: string; pagina: number } }[]
  } | null>(null)
  const [custos, setCustos] = useState<{ itens: { etapa: string; custo_brl: number }[]; total_brl: number } | null>(null)

  const totalPerguntas = cfg?.limites.perguntas_chat ?? 3
  const restantes = caderno?.restantes ?? 0

  useEffect(() => {
    api.get<Configuracao>('/v1/configuracao').then(setCfg).catch(() => null)
  }, [])

  useEffect(() => {
    if (!cadernoId) return
    setErro('')
    setCorrigido(null)
    const st = location.state as { perguntaInicial?: string; trilhaPronta?: boolean; reaproveitado?: boolean } | null
    const comPergunta = Boolean(st?.perguntaInicial)
    setView(comPergunta ? 'chat' : 'resumo')
    setConcluidos(comPergunta ? new Set<View>(['resumo', 'mapa', 'quiz']) : new Set())
    setModoFoco(Boolean(st?.trilhaPronta) || (Boolean(st?.reaproveitado) && !comPergunta))
    setBannerTrilha(Boolean(st?.trilhaPronta) || (Boolean(st?.reaproveitado) && !comPergunta))
    setReaproveitado(Boolean(st?.reaproveitado))
    setProntoChat(false)
    api.get<Caderno>(`/v1/cadernos/${cadernoId}`).then((c) => {
      setCaderno(c)
      setFontesSidebar(c.fontes)
    }).catch((e) => setErro(e.message))
    api.get<Mensagem[]>(`/v1/cadernos/${cadernoId}/mensagens`)
      .then((m) => {
        setMensagens(m)
        setProntoChat(true)
      })
      .catch(() => { setMensagens([]); setProntoChat(true) })
    api.get<{ quiz: typeof quiz; resultados: { nota: number }[] }>(`/v1/cadernos/${cadernoId}/quiz`)
      .then((d) => {
        setResultados(d.resultados)
      })
      .catch(() => null)
    api.get<{ itens: { etapa: string; custo_brl: number }[]; total_brl: number }>(`/v1/cadernos/${cadernoId}/custos`)
      .then(setCustos).catch(() => setCustos(null))
  }, [cadernoId, setFontesSidebar, location.state])

  function etapaLiberada(etapa: View): boolean {
    const idx = ORDEM_TRILHA.indexOf(etapa)
    if (idx <= 0) return true
    // Libera se todas as anteriores foram concluídas
    return ORDEM_TRILHA.slice(0, idx).every((e) => concluidos.has(e))
  }

  function irPara(proxima: View) {
    if (!etapaLiberada(proxima) && !concluidos.has(proxima)) return
    setView(proxima)
  }

  function concluirEtapaAtual() {
    const i = ORDEM_TRILHA.indexOf(view)
    setConcluidos((c) => new Set(c).add(view))
    if (i >= 0 && i < ORDEM_TRILHA.length - 1) {
      const prox = ORDEM_TRILHA[i + 1]
      setView(prox)
      return
    }
    // Última etapa (dúvidas): sai do modo foco
    setModoFoco(false)
  }

  useEffect(() => {
    if (!cadernoId || view !== 'chat' || mensagens.length > 0 || restantes <= 0) {
      setSugestoes([])
      return
    }
    api.get<string[]>(`/v1/cadernos/${cadernoId}/sugestoes`).then(setSugestoes).catch(() => setSugestoes([]))
  }, [cadernoId, view, mensagens.length, restantes])

  useEffect(() => {
    if (!cadernoId || view !== 'resumo') return
    api.get<typeof resumo>(`/v1/cadernos/${cadernoId}/resumo`).then(setResumo).catch((e) => setErro(e.message))
  }, [cadernoId, view])

  useEffect(() => {
    if (!cadernoId || view !== 'mapa') return
    api.get<{ mapa: Mapa; dot: string }>(`/v1/cadernos/${cadernoId}/mapa`).then(async (d) => {
      setMapa(d.mapa)
      setDot(d.dot)
      setNoSel(d.mapa.nos[0]?.id || '')
    }).catch((e) => setErro(e.message))
  }, [cadernoId, view])

  useEffect(() => {
    if (!dot) return
    let cancel = false
    instance().then((viz) => {
      const out = viz.renderString(dot, { format: 'svg' })
      if (!cancel) setSvg(out)
    }).catch(() => setSvg(''))
    return () => { cancel = true }
  }, [dot, mapa])

  useEffect(() => {
    if (!cadernoId || view !== 'mapa' || !noSel) return
    api.get<{ texto: string; imagens: string[] }>(`/v1/cadernos/${cadernoId}/mapa/trecho?no_id=${encodeURIComponent(noSel)}`)
      .then(setTrecho).catch(() => setTrecho(null))
  }, [cadernoId, view, noSel])

  useEffect(() => {
    if (!cadernoId || view !== 'quiz') return
    api.get<{ quiz: typeof quiz; resultados: { nota: number }[] }>(`/v1/cadernos/${cadernoId}/quiz`)
      .then((d) => { setQuiz(d.quiz); setResultados(d.resultados) })
      .catch((e) => setErro(e.message))
  }, [cadernoId, view])

  const porId = useMemo(() => Object.fromEntries((mapa?.nos || []).map((n) => [n.id, n])), [mapa])

  async function enviarPergunta(texto: string) {
    const q = texto.trim()
    if (!q || !cadernoId || restantes <= 0) return
    setPerguntando(true)
    setErro('')
    try {
      const r = await api.post<Mensagem & { restantes: number }>(`/v1/cadernos/${cadernoId}/mensagens`, { pergunta: q })
      setMensagens((m) => [...m, { pergunta: r.pergunta, resposta: r.resposta, fontes: r.fontes, sem_base: r.sem_base }])
      setCaderno((c) => c ? { ...c, restantes: r.restantes } : c)
      setPergunta('')
      setSugestoes([])
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Falha ao perguntar.')
    } finally {
      setPerguntando(false)
    }
  }

  useEffect(() => {
    if (!prontoChat || !perguntaPendente || !caderno || perguntando) return
    if ((caderno.restantes ?? 0) <= 0) {
      setPerguntaPendente('')
      return
    }
    const q = perguntaPendente
    setPerguntaPendente('')
    void enviarPergunta(q)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prontoChat, perguntaPendente, caderno?.id, caderno?.restantes])

  async function renomear() {
    if (!caderno) return
    const titulo = prompt('Renomear caderno', caderno.titulo)
    if (!titulo?.trim()) return
    const c = await api.patch<Caderno>(`/v1/cadernos/${caderno.id}`, { titulo: titulo.trim() })
    setCaderno({ ...caderno, ...c })
    await recarregarCadernos()
  }

  function adicionarNo() {
    if (!mapa || !novoNo.trim()) return
    const novo = `u${mapa.nos.length + 1}_${Math.abs(hash(novoNo)) % 9999}`
    const fonte = (paiNo && porId[paiNo]?.fonte) || mapa.nos[0]?.fonte || { arquivo: 'material.pdf', pagina: 1 }
    const next = {
      nos: [...mapa.nos, { id: novo, rotulo: novoNo.trim(), fonte }],
      relacoes: paiNo
        ? [...mapa.relacoes, { de: paiNo, para: novo, tipo: 'relaciona-se' }]
        : [...mapa.relacoes],
    }
    setMapa(next)
    setDot(localDot(next))
    setNovoNo('')
  }

  function removerNo(rem: string) {
    if (!mapa) return
    const next = {
      nos: mapa.nos.filter((n) => n.id !== rem),
      relacoes: mapa.relacoes.filter((r) => rem !== r.de && rem !== r.para),
    }
    setMapa(next)
    setDot(localDot(next))
    if (noSel === rem) setNoSel(next.nos[0]?.id || '')
  }

  async function corrigirQuiz(e: FormEvent) {
    e.preventDefault()
    if (!cadernoId) return
    const r = await api.post<NonNullable<typeof corrigido>>(`/v1/cadernos/${cadernoId}/quiz/correcoes`, { respostas })
    setCorrigido(r)
    setResultados((prev) => [{ nota: r.nota }, ...prev])
  }

  if (erro && !caderno) return <div className="erro">{erro}</div>
  if (!caderno) return <p className="sub">Carregando caderno…</p>

  const fontesCount = caderno.fontes?.length ?? 0
  const pags = caderno.total_paginas ?? 0
  const idxAtual = ORDEM_TRILHA.indexOf(view)
  const rotuloProxima = idxAtual >= 0 && idxAtual < ORDEM_TRILHA.length - 1
    ? VISOES[idxAtual + 1].label
    : null

  const conteudoEtapa = (
    <>
      {view === 'chat' && (
        <>
          <div className="guia" style={{ marginTop: '1rem' }}>
            Olá, <b>{primeiroNome(usuario?.nome || '')}</b>! Esta é a <b>última etapa</b> da trilha.
            Li <b>{fontesCount}</b> fonte(s) e já preparei resumo, mapa e quiz. Pergunte o que ficou confuso:
            respondo só com base no seu material, sempre citando arquivo e página.
          </div>
          <div className="chat-lista">
            {mensagens.map((m, i) => (
              <div key={i}>
                <div className="msg-user">{m.pergunta}</div>
                <div className="msg-bot">
                  <div>{m.resposta}</div>
                  <div>{m.fontes?.map((f, j) => <Citacao key={j} fonte={f} />)}</div>
                </div>
              </div>
            ))}
          </div>
          {sugestoes.length > 0 && (
            <div>
              <p className="sub" style={{ fontSize: '0.85rem' }}>Sugestões para começar</p>
              {sugestoes.map((s) => (
                <button key={s} className="btn pill" type="button" onClick={() => enviarPergunta(s)}>{s}</button>
              ))}
            </div>
          )}
          {restantes <= 0 && <div className="ok">Você usou todas as perguntas deste caderno. Bons estudos!</div>}
          <form className="chat-form" onSubmit={(e) => { e.preventDefault(); enviarPergunta(pergunta) }}>
            <input
              value={pergunta}
              onChange={(e) => setPergunta(e.target.value)}
              disabled={restantes <= 0 || perguntando}
              placeholder="Pergunte sobre um conceito do material"
            />
            <button className="btn primary" disabled={restantes <= 0 || perguntando || !pergunta.trim()}>
              {perguntando ? '…' : '↑'}
            </button>
          </form>
          {!concluidos.has('chat') && (
            <button className="btn" type="button" style={{ marginTop: '1rem', width: 'auto' }} onClick={concluirEtapaAtual}>
              Encerrar trilha
            </button>
          )}
        </>
      )}

      {view === 'resumo' && resumo && (
        <>
          <div className="painel-titulo" style={{ marginTop: '1rem' }}><span className="ponto" />Resumo por tópicos</div>
          {resumo.topicos.map((tp, i) => (
            <div className="topico" key={i}>
              <div className="t">{tp.titulo}</div>
              <div dangerouslySetInnerHTML={{ __html: negritoHtml(tp.texto_destacado) }} />
              <div style={{ marginTop: '0.5rem' }}><Citacao fonte={tp.fonte} /></div>
            </div>
          ))}
          <div className="painel-titulo"><span className="ponto" />Termos-chave para memorizar</div>
          {resumo.termos.map((t) => (
            <div className="termo" key={t.termo}><b>{t.termo}</b><span>{t.definicao}</span></div>
          ))}
          <button className="btn primary" type="button" style={{ marginTop: '1rem', width: 'auto' }} onClick={concluirEtapaAtual}>
            Concluí a leitura · Ir para {rotuloProxima} →
          </button>
        </>
      )}
      {view === 'resumo' && !resumo && <p className="sub" style={{ marginTop: '1rem' }}>Carregando resumo…</p>}

      {view === 'mapa' && mapa && (
        <>
          <div className="painel-titulo" style={{ marginTop: '1rem' }}><span className="ponto" />Mapa mental</div>
          <div className="mapa-svg" dangerouslySetInnerHTML={{ __html: svg }} />
          {mapa.nos.length > 0 && (
            <div className="field">
              <label>Ver o trecho de um nó</label>
              <select value={noSel} onChange={(e) => setNoSel(e.target.value)}>
                {mapa.nos.map((n) => <option key={n.id} value={n.id}>{n.rotulo}</option>)}
              </select>
            </div>
          )}
          {noSel && porId[noSel] && <Citacao fonte={porId[noSel].fonte} />}
          {trecho && <pre style={{ whiteSpace: 'pre-wrap', color: 'var(--suave)', fontSize: '0.88rem' }}>{trecho.texto}</pre>}
          {trecho?.imagens?.map((src) => (
            <img key={src} src={apiUrl(src)} alt="" style={{ maxWidth: 260, borderRadius: 12, marginRight: 8 }} />
          ))}
          <details className="expander">
            <summary>Editar mapa (adicionar/remover nós)</summary>
            <div className="field" style={{ marginTop: '0.8rem' }}>
              <label>Novo nó</label>
              <input value={novoNo} onChange={(e) => setNovoNo(e.target.value)} />
            </div>
            <div className="field">
              <label>Ligar a</label>
              <select value={paiNo} onChange={(e) => setPaiNo(e.target.value)}>
                <option value="">—</option>
                {mapa.nos.map((n) => <option key={n.id} value={n.id}>{n.rotulo}</option>)}
              </select>
            </div>
            <button className="btn primary" type="button" onClick={adicionarNo}>Adicionar</button>
            {mapa.nos.length > 0 && (
              <div className="field" style={{ marginTop: '0.8rem' }}>
                <label>Remover nó</label>
                <select id="rem" defaultValue={mapa.nos[0].id}>
                  {mapa.nos.map((n) => <option key={n.id} value={n.id}>{n.rotulo}</option>)}
                </select>
                <button className="btn" type="button" style={{ marginTop: '0.5rem' }}
                  onClick={() => {
                    const el = document.getElementById('rem') as HTMLSelectElement
                    removerNo(el.value)
                  }}>Remover</button>
              </div>
            )}
          </details>
          <button className="btn primary" type="button" style={{ marginTop: '1rem', width: 'auto' }} onClick={concluirEtapaAtual}>
            Concluí o mapa · Ir para {rotuloProxima} →
          </button>
        </>
      )}
      {view === 'mapa' && !mapa && <p className="sub" style={{ marginTop: '1rem' }}>Carregando mapa…</p>}

      {view === 'quiz' && quiz && (
        <>
          <div className="painel-titulo" style={{ marginTop: '1rem' }}><span className="ponto" />Quiz</div>
          {!quiz.questoes.length ? (
            <div className="erro">Não foi possível gerar questões com este material (conteúdo insuficiente).</div>
          ) : (
            <form onSubmit={corrigirQuiz}>
              {quiz.questoes.map((q, i) => (
                <div className="questao" key={i}>
                  <div><b>{i + 1}.</b> {q.enunciado} <span className="nivel">{q.nivel}</span></div>
                  <div className="alts">
                    {(['A', 'B', 'C', 'D'] as const).map((L, idx) => (
                      <label key={L}>
                        <input
                          type="radio"
                          name={`q${i}`}
                          value={L}
                          disabled={!!corrigido}
                          checked={respostas[i] === L}
                          onChange={() => setRespostas((r) => ({ ...r, [i]: L }))}
                        />
                        <span>{L}) {q.alternativas[idx]}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
              <button className="btn primary" type="submit" disabled={!!corrigido}>Corrigir</button>
            </form>
          )}
          {corrigido && (
            <div style={{ marginTop: '1rem' }}>
              <div className="stat" style={{ marginBottom: '0.8rem' }}>
                <div className="n">{corrigido.nota}/10</div>
                <div className="l">{corrigido.acertos} de {corrigido.total} acertos</div>
              </div>
              {corrigido.itens.filter((it) => !it.acertou).map((it) => (
                <div className="topico" key={it.indice}>
                  <div><b>Questão {it.indice + 1}</b>: você marcou {it.marcada || '—'}; gabarito {it.gabarito}.</div>
                  <p>{it.justificativa}</p>
                  <Citacao fonte={it.fonte} />
                </div>
              ))}
              <button className="btn" type="button" onClick={() => { setCorrigido(null); setRespostas({}) }}>Refazer quiz</button>
            </div>
          )}
          {(corrigido || !quiz.questoes.length) && (
            <button className="btn primary" type="button" style={{ marginTop: '1rem', width: 'auto' }} onClick={concluirEtapaAtual}>
              Concluí o quiz · Ir para {rotuloProxima} →
            </button>
          )}
          {!corrigido && quiz.questoes.length > 0 && (
            <p className="sub" style={{ marginTop: '0.8rem', fontSize: '0.85rem' }}>
              Corrija o quiz para liberar a próxima etapa.
            </p>
          )}
        </>
      )}
      {view === 'quiz' && !quiz && <p className="sub" style={{ marginTop: '1rem' }}>Carregando quiz…</p>}
    </>
  )

  return (
    <div className="caderno-layout">
      <div className="painel">
        <button className="btn ghost" style={{ marginBottom: '0.8rem' }} onClick={() => nav('/')}>← Voltar ao menu principal</button>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
          <div>
            <div className="hero-icone"><img src="/atitus_icone.png" alt="" /></div>
            <h1 className="hero-titulo">{caderno.titulo}</h1>
            <div className="hero-meta">{fontesCount} fonte(s) · {pags} páginas/slides · criado em {dataCurta(caderno.criado_em)}</div>
          </div>
          <button className="btn" style={{ width: 'auto', height: 'fit-content' }} onClick={renomear}>✎</button>
        </div>
        {bannerTrilha && !modoFoco && (
          <div className="ok" style={{ marginTop: '1rem' }}>
            <div>
              Sua trilha já está pronta: preparei <b>resumo</b>, <b>mapa mental</b> e <b>quiz</b> com base no seu material.
              Conclua cada etapa na ordem (Resumo → Mapa → Quiz → Dúvidas).
            </div>
            <button className="btn" type="button" style={{ width: 'auto', marginTop: '0.6rem' }}
              onClick={() => { setBannerTrilha(false); setModoFoco(true) }}>Começar trilha</button>
          </div>
        )}
        {reaproveitado && (
          <div className="ok">
            Material já processado antes: conteúdo reaproveitado do cache, sem novas chamadas ao modelo.
            <button className="btn" type="button" style={{ width: 'auto', marginLeft: '0.5rem' }}
              onClick={() => setReaproveitado(false)}>Ok</button>
          </div>
        )}

        {!modoFoco && (
          <>
            <div className="trilha-stepper" aria-label="Sua trilha de estudo">
              <div className="rotulo-secao" style={{ marginTop: 0 }}>Sua trilha</div>
              <div className="trilha-passos">
                {VISOES.map((v, i) => {
                  const liberada = etapaLiberada(v.key) || concluidos.has(v.key)
                  return (
                    <button
                      key={v.key}
                      type="button"
                      disabled={!liberada}
                      className={`trilha-passo ${view === v.key ? 'ativo' : ''} ${concluidos.has(v.key) ? 'visitado' : ''} ${!liberada ? 'bloqueado' : ''}`}
                      onClick={() => irPara(v.key)}
                    >
                      <span className="trilha-num">{concluidos.has(v.key) ? '✓' : i + 1}</span>
                      <span className="trilha-label">{v.label}</span>
                    </button>
                  )
                })}
              </div>
              <p className="sub" style={{ fontSize: '0.8rem', margin: '0.35rem 0 0' }}>
                Conclua uma etapa para liberar a próxima
              </p>
            </div>

            {erro && <div className="erro">{erro}</div>}
            {conteudoEtapa}
          </>
        )}
      </div>

      <div className="painel">
        <div className="painel-titulo"><span className="ponto" />Estúdio</div>
        <p className="sub" style={{ fontSize: '0.8rem', margin: '0 0 0.7rem' }}>
          Trilha em ordem · etapas futuras ficam bloqueadas
        </p>
        {VISOES.map((v) => {
          const liberada = etapaLiberada(v.key) || concluidos.has(v.key)
          return (
            <button
              key={v.key}
              className={`btn estudio ${view === v.key ? 'active' : ''}`}
              style={{ marginBottom: '0.45rem', opacity: liberada ? 1 : 0.45 }}
              disabled={!liberada}
              onClick={() => { irPara(v.key); if (!modoFoco) setModoFoco(true) }}
            >
              {concluidos.has(v.key) ? '✓ ' : !liberada ? '🔒 ' : ''}{v.label}
            </button>
          )
        })}
        <div className="rotulo-secao">Seu progresso</div>
        <p className="sub" style={{ fontSize: '0.9rem', margin: 0 }}>
          Perguntas restantes: <b>{restantes} de {totalPerguntas}</b>
        </p>
        <div className="progress"><span style={{ width: `${totalPerguntas ? (restantes / totalPerguntas) * 100 : 0}%` }} /></div>
        {resultados.length > 0 ? (
          <div>
            <span className="chip">Última nota {resultados[0].nota.toFixed(1)}/10</span>
            <span className="chip neutro">Melhor {Math.max(...resultados.map((r) => r.nota)).toFixed(1)}</span>
            <span className="chip neutro">{resultados.length} tentativa(s)</span>
          </div>
        ) : (
          <p className="sub" style={{ fontSize: '0.85rem' }}>Você ainda não fez o quiz deste caderno.</p>
        )}
        <details className="expander">
          <summary>Custo estimado do caderno</summary>
          {custos?.itens?.length ? (
            <ul style={{ color: 'var(--suave)', fontSize: '0.85rem' }}>
              {custos.itens.map((u, i) => (
                <li key={i}>{u.etapa}: R$ {Number(u.custo_brl).toFixed(4)}</li>
              ))}
            </ul>
          ) : <p className="sub" style={{ fontSize: '0.85rem' }}>Sem uso registrado.</p>}
          <p>Total: R$ {(custos?.total_brl ?? 0).toFixed(4)}</p>
        </details>
      </div>

      {modoFoco && (
        <div className="trilha-modal" role="dialog" aria-modal="true" aria-label="Trilha de estudo">
          <div className="trilha-modal-painel">
            <div className="trilha-modal-topo">
              <div>
                <div className="rotulo-secao" style={{ marginTop: 0 }}>Trilha guiada</div>
                <h2 className="trilha-modal-titulo">{caderno.titulo}</h2>
                <p className="sub" style={{ margin: 0, fontSize: '0.85rem' }}>
                  Etapa {idxAtual + 1} de {ORDEM_TRILHA.length}: <b>{VISOES[idxAtual]?.label}</b>
                </p>
              </div>
              <button
                className="btn ghost"
                type="button"
                style={{ width: 'auto' }}
                onClick={() => setModoFoco(false)}
                title="Minimizar (a ordem continua bloqueada)"
              >
                Minimizar
              </button>
            </div>
            <div className="trilha-passos" style={{ marginBottom: '0.75rem' }}>
              {VISOES.map((v, i) => {
                const liberada = etapaLiberada(v.key) || concluidos.has(v.key)
                return (
                  <button
                    key={v.key}
                    type="button"
                    disabled={!liberada}
                    className={`trilha-passo ${view === v.key ? 'ativo' : ''} ${concluidos.has(v.key) ? 'visitado' : ''} ${!liberada ? 'bloqueado' : ''}`}
                    onClick={() => irPara(v.key)}
                  >
                    <span className="trilha-num">{concluidos.has(v.key) ? '✓' : i + 1}</span>
                    <span className="trilha-label">{v.label}</span>
                  </button>
                )
              })}
            </div>
            {erro && <div className="erro">{erro}</div>}
            <div className="trilha-modal-corpo">{conteudoEtapa}</div>
          </div>
        </div>
      )}
    </div>
  )
}

function hash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0
  return h
}

function localDot(mapa: Mapa): string {
  const esc = (s: string) => String(s).replace(/\\/g, '').replace(/"/g, "'")
  const linhas = [
    'digraph G { bgcolor="transparent"; rankdir=LR; pad=0.2; nodesep=0.2; ranksep=0.9;',
    'node [shape=box, style="rounded,filled", fillcolor="#172033", color="#22d3ee", fontcolor="#e6e9ef", fontname="Helvetica", penwidth=1.3, margin="0.18,0.1"];',
    'edge [color="#4b5873", fontcolor="#8b93a7", fontname="Helvetica", fontsize=9, arrowsize=0.7];',
  ]
  for (const n of mapa.nos) linhas.push(`"${esc(n.id)}" [label="${esc(n.rotulo)}\\n(p. ${n.fonte.pagina})"];`)
  for (const r of mapa.relacoes) {
    const attrs = String(r.tipo).toLowerCase().startsWith('relaciona')
      ? 'style=dashed, constraint=false, arrowhead=none'
      : `label="${esc(r.tipo)}"`
    linhas.push(`"${esc(r.de)}" -> "${esc(r.para)}" [${attrs}];`)
  }
  return linhas.join('\n') + '}'
}
