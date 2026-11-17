# Deploy no Railway (front + API no mesmo projeto)

O erro **Railpack failed to prepare the build** acontece quando o serviço aponta para a **raiz** do monorepo (não há `package.json` nem `requirements.txt` ali). Use **dois serviços**, cada um com Root Directory.

## 1. Serviço `trilha-api` (backend)

1. New → GitHub → `Trilha-Atitus`
2. **Root Directory:** `backend`
3. Variáveis (opcional):
   - `CORS_ORIGINS` = URL do front (ex.: `https://trilha-web-production.up.railway.app`)
   - `GEMINI_API_KEY` = chave do Google AI Studio (Gemini); sem isso a API fica em modo offline
4. **Volume (obrigatório para não perder usuários):**
   - No serviço da API → **Settings** → **Volumes** → **Add Volume**
   - Mount path: `/data`
   - A variável `TRILHA_DATA_DIR=/data` já vem no Dockerfile (usuários e cache SQLite ficam aí)
   - Sem volume, **cada redeploy apaga** contas, sessões e cadernos
5. Start já definido no Dockerfile (`uvicorn` + criação de `/data`)
6. Healthcheck: `/health`

Anote a URL pública da API (ex.: `https://trilha-api-production.up.railway.app`).

## 2. Serviço `trilha-web` (frontend)

1. No **mesmo** projeto Railway → Add Service → mesmo repo
2. **Root Directory:** `frontend`
3. Variáveis:
   - `VITE_API_URL` = URL da API **sem** barra no final  
     (ex.: `https://trilha-api-production.up.railway.app`)
4. Build: `npm ci && npm run build`
5. Start: `npx serve -s dist -l $PORT`

`VITE_*` entra no build: se mudar a URL da API, faça **Redeploy** do front.

## 3. Ordem

1. Suba a API e confira `https://SUA-API/health` → `{"status":"ok"}`.
2. Configure `VITE_API_URL` e `CORS_ORIGINS`.
3. Suba o front.
4. Abra a URL do front, crie conta e teste um PDF.

## Não faça

- Um único serviço na raiz `./`
- Preset “Services” / Zola no backend
- Esquecer o volume: sem volume o SQLite some a cada redeploy
