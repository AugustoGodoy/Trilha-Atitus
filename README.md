# Trilha Atitus

Plataforma de estudo guiado com tutor inteligente. O aluno envia os slides ou PDFs da aula e segue uma jornada curta e guiada: **resumo, mapa mental, quiz e dúvidas**, sempre com citação de arquivo e página/slide.

Projeto do Grupo 4 da Universidade Atitus. A especificação, com o status de cada requisito, está em [`docs/specs.md`](docs/specs.md) (versão em PDF: [`docs/specs.pdf`](docs/specs.pdf)).

## Sumário

1. [Arquitetura](#1-arquitetura)
2. [Funcionalidades](#2-funcionalidades)
3. [Como executar](#3-como-executar)
4. [Configuração e modo de geração](#4-configuração-e-modo-de-geração)
5. [Dados e segurança](#5-dados-e-segurança)
6. [Estrutura do projeto](#6-estrutura-do-projeto)
7. [Requisitos implementados](#7-requisitos-implementados)
8. [Decisões e limitações](#8-decisões-e-limitações)

## 1. Arquitetura

Monorepo com API e front separados:

| Camada | Stack |
|---|---|
| **API** | FastAPI (Python 3.12) em `backend/`, reutilizando o domínio `estudo_guiado/` |
| **Front** | React + TypeScript + Vite em `frontend/` |
| **Persistência** | SQLite (`app.sqlite` + `cache.sqlite`) |
| **Recuperação** | BM25 local |
| **Geração** | Offline extrativo ou LLM via API OpenAI-compatible (`gpt-4o-mini`) |

Contrato REST versionado em `/v1/...`, com autenticação `Authorization: Bearer <token>`. Documentação OpenAPI em `http://localhost:8000/docs`.

## 2. Funcionalidades

- **Login e cadastro** com e-mail e senha. Cada aluno vê apenas os próprios cadernos.
- **Cadernos**: cada material enviado (PDF ou PPTX) vira um caderno salvo na conta, com histórico de conversa e notas de quiz.
- **Estúdio** com quatro visões, percorridas em **ordem obrigatória** (trilha sequencial: cada etapa só libera a próxima depois de concluída; etapas futuras aparecem bloqueadas 🔒):
  1. **Resumo**: tópicos com termos-chave destacados e fonte.
  2. **Mapa mental**: JSON + Graphviz (renderizado no browser com `@viz-js/viz`); editável na sessão.
  3. **Quiz**: 5 questões com gabarito, justificativa, fonte e correção automática.
  4. **Dúvidas**: chat com limite de perguntas por caderno; cita arquivo e página; recusa quando não há base.
- **Painel inicial** com saudação, estatísticas e envio de novo material.
- **Custo controlado**: limites validados antes do processamento; geração única e cache por hash.

## 3. Como executar

Requer Python 3.12+ e Node.js 20+.

### API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### Front

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxy para a API em :8000)
```

### Testes

```bash
cd backend
pytest
```

No primeiro acesso, use a aba **Criar conta** da tela de login.

## 4. Configuração e modo de geração

Modelo, URL, preços e limites ficam em [`backend/config.toml`](backend/config.toml).

| Limite | Valor |
|---|---|
| Páginas/slides por jornada | 40 |
| Tamanho por arquivo | 20 MB |
| Perguntas no chat | 3 por caderno |
| Questões no quiz | 5 |
| Jornadas por dia | 20 por usuário |

**Sem chave de API**, a API roda em **modo offline** (geração extrativa, custo zero).

**Com chave de API**:

```bash
export OPENAI_API_KEY=...     # fica só no servidor; o aluno nunca vê a chave
```

## 5. Dados e segurança

- **Banco SQLite** em `backend/data/app.sqlite` (fora do Git): usuários, sessões, cadernos, mensagens e resultados de quiz.
- **Cache** em `backend/data/cache.sqlite`, por hash dos arquivos.
- **Senhas** com scrypt e salt; a senha nunca é armazenada.
- **Sessão** por token opaco (só o hash no banco, validade 7 dias); o front guarda o token em `localStorage`.
- **Bloqueio** após 5 falhas de login em 10 minutos.
- **Aviso permanente** de que o app é ferramenta de apoio e não substitui o professor.

## 6. Estrutura do projeto

```
backend/
  api/                 FastAPI: rotas /v1, auth Bearer, erros padronizados
  estudo_guiado/       Domínio (extração, BM25, geração, banco, segurança)
  config.toml          Limites, modelo, cache e caminhos
  tests/               pytest (domínio + API)
frontend/
  src/pages/           Login, Home, Caderno
  src/components/      Layout, Sidebar
  src/styles/theme.css Tema escuro (paridade visual)
  public/              Logo e ícone da Atitus
docs/                  Especificação (specs.md / specs.pdf)
assets/                Logos originais
```

## 7. Requisitos implementados

| Spec | Implementação |
|---|---|
| RF01-03 | Extração PDF/PPTX, chunking e índice BM25 |
| RF02 | Validação de limites antes do LLM (`Servico.validar`) |
| RF04 | Resumo por tópicos com fonte e termos-chave |
| RF05-06 | Mapa mental JSON + Graphviz; edição local de nós |
| RF07-08 | Quiz com gabarito e correção no servidor |
| RF09-10 | Chat com 3 perguntas, citação e recusa |
| RF11 | Cache por hash; reabrir não chama o LLM |
| RF12 | Custos por etapa no cache |
| RF13 | Aviso permanente de ferramenta de apoio |

Status completo em [`docs/specs.md`](docs/specs.md).

## 8. Decisões e limitações

- **Recuperação**: BM25 local; trocar por embeddings é isolado em `retrieval.py`.
- **Mapa mental**: edição só na sessão do browser (não persiste).
- **Pergunta recusada** não consome o limite (configurável).
- **Modo offline**: quiz de lacunas; níveis variados de Bloom só com LLM.
- **Pendências**: aviso de privacidade/consentimento, exclusão de conta, avaliação quantitativa, PDFs escaneados.
