"""Banco SQLite da aplicação: usuários, sessões, cadernos (jornadas por usuário), chat e resultados de quiz.

O conteúdo gerado pelo LLM continua no cache por hash (cache.py); aqui fica tudo que é do usuário.
"""
import json
import sqlite3
import threading
import time
from pathlib import Path

from . import seguranca

JANELA_BLOQUEIO_S = 600
MAX_FALHAS_LOGIN = 5
VALIDADE_SESSAO_S = 7 * 24 * 3600

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    criado_em REAL NOT NULL,
    ultimo_acesso REAL
);
CREATE TABLE IF NOT EXISTS sessoes (
    token_hash TEXT PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    criada_em REAL NOT NULL,
    expira_em REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tentativas_login (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    ts REAL NOT NULL,
    sucesso INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tentativas_email_ts ON tentativas_login (email, ts);
CREATE TABLE IF NOT EXISTS cadernos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo TEXT NOT NULL,
    hash TEXT NOT NULL,
    criado_em REAL NOT NULL,
    atualizado_em REAL NOT NULL,
    UNIQUE (usuario_id, hash)
);
CREATE TABLE IF NOT EXISTS mensagens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caderno_id INTEGER NOT NULL REFERENCES cadernos(id) ON DELETE CASCADE,
    pergunta TEXT NOT NULL,
    resposta TEXT NOT NULL,
    fontes TEXT NOT NULL,
    sem_base INTEGER NOT NULL,
    consumiu INTEGER NOT NULL,
    ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS resultados_quiz (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caderno_id INTEGER NOT NULL REFERENCES cadernos(id) ON DELETE CASCADE,
    nota REAL NOT NULL,
    acertos INTEGER NOT NULL,
    total INTEGER NOT NULL,
    ts REAL NOT NULL
);
"""


class ErroAutenticacao(Exception):
    """Mensagem segura para exibir ao usuário."""


class Banco:
    def __init__(self, caminho: str):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.db = sqlite3.connect(self.caminho, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self._lock:
            self.db.execute("PRAGMA foreign_keys = ON")
            self.db.execute("PRAGMA journal_mode = WAL")
            self.db.executescript(SCHEMA)

    # ------------------------------------------------------------ infra

    def _escrever(self, sql: str, params: tuple = ()) -> int:
        with self._lock:
            cur = self.db.execute(sql, params)
            self.db.commit()
            return cur.lastrowid

    def _um(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._lock:
            return self.db.execute(sql, params).fetchone()

    def _todos(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self.db.execute(sql, params).fetchall()

    # ------------------------------------------------------------ usuários

    def criar_usuario(self, nome: str, email: str, senha: str) -> dict:
        nome, email = " ".join(nome.split()), seguranca.normalizar_email(email)
        if len(nome) < 2:
            raise ErroAutenticacao("Informe seu nome.")
        if not seguranca.email_valido(email):
            raise ErroAutenticacao("Informe um e-mail válido.")
        if erro := seguranca.validar_senha(senha):
            raise ErroAutenticacao(erro)
        try:
            uid = self._escrever(
                "INSERT INTO usuarios (nome, email, senha_hash, criado_em, ultimo_acesso) VALUES (?,?,?,?,?)",
                (nome, email, seguranca.hash_senha(senha), time.time(), time.time()))
        except sqlite3.IntegrityError as e:
            raise ErroAutenticacao("Já existe uma conta com este e-mail.") from e
        return self.usuario(uid)

    def usuario(self, uid: int) -> dict | None:
        r = self._um("SELECT id, nome, email, criado_em, ultimo_acesso FROM usuarios WHERE id=?", (uid,))
        return dict(r) if r else None

    def autenticar(self, email: str, senha: str) -> dict:
        email = seguranca.normalizar_email(email)
        if self._falhas_recentes(email) >= MAX_FALHAS_LOGIN:
            raise ErroAutenticacao("Muitas tentativas. Aguarde alguns minutos e tente novamente.")
        r = self._um("SELECT * FROM usuarios WHERE email=?", (email,))
        # verifica mesmo sem usuário para manter o tempo de resposta parecido
        hash_ref = r["senha_hash"] if r else seguranca.hash_senha("x")
        ok = seguranca.verificar_senha(senha, hash_ref) and r is not None
        self._escrever("INSERT INTO tentativas_login (email, ts, sucesso) VALUES (?,?,?)", (email, time.time(), int(ok)))
        if not ok:
            raise ErroAutenticacao("E-mail ou senha incorretos.")
        self._escrever("UPDATE usuarios SET ultimo_acesso=? WHERE id=?", (time.time(), r["id"]))
        return self.usuario(r["id"])

    def _falhas_recentes(self, email: str) -> int:
        limite = time.time() - JANELA_BLOQUEIO_S
        ultimo_ok = self._um("SELECT MAX(ts) AS t FROM tentativas_login WHERE email=? AND sucesso=1", (email,))["t"] or 0
        return self._um("SELECT COUNT(*) AS n FROM tentativas_login WHERE email=? AND sucesso=0 AND ts>?",
                        (email, max(limite, ultimo_ok)))["n"]

    # ------------------------------------------------------------ sessões

    def criar_sessao(self, uid: int) -> str:
        token = seguranca.novo_token()
        agora = time.time()
        self._escrever("INSERT INTO sessoes (token_hash, usuario_id, criada_em, expira_em) VALUES (?,?,?,?)",
                       (seguranca.hash_token(token), uid, agora, agora + VALIDADE_SESSAO_S))
        self._escrever("DELETE FROM sessoes WHERE expira_em < ?", (agora,))
        return token

    def usuario_da_sessao(self, token: str) -> dict | None:
        r = self._um("SELECT usuario_id FROM sessoes WHERE token_hash=? AND expira_em>?",
                     (seguranca.hash_token(token), time.time()))
        return self.usuario(r["usuario_id"]) if r else None

    def encerrar_sessao(self, token: str) -> None:
        self._escrever("DELETE FROM sessoes WHERE token_hash=?", (seguranca.hash_token(token),))

    # ------------------------------------------------------------ cadernos

    def registrar_caderno(self, uid: int, hash_conteudo: str, titulo: str) -> int:
        """Cria o caderno do usuário (ou reaproveita o mesmo material já enviado por ele)."""
        agora = time.time()
        existente = self._um("SELECT id FROM cadernos WHERE usuario_id=? AND hash=?", (uid, hash_conteudo))
        if existente:
            self._escrever("UPDATE cadernos SET atualizado_em=? WHERE id=?", (agora, existente["id"]))
            return existente["id"]
        return self._escrever(
            "INSERT INTO cadernos (usuario_id, titulo, hash, criado_em, atualizado_em) VALUES (?,?,?,?,?)",
            (uid, titulo, hash_conteudo, agora, agora))

    def caderno(self, uid: int, caderno_id: int) -> dict | None:
        r = self._um("SELECT * FROM cadernos WHERE id=? AND usuario_id=?", (caderno_id, uid))
        return dict(r) if r else None

    def listar_cadernos(self, uid: int) -> list[dict]:
        return [dict(r) for r in self._todos("""
            SELECT c.*, (SELECT MAX(nota) FROM resultados_quiz q WHERE q.caderno_id=c.id) AS melhor_nota,
                   (SELECT COUNT(*) FROM mensagens m WHERE m.caderno_id=c.id) AS perguntas
            FROM cadernos c WHERE c.usuario_id=? ORDER BY c.atualizado_em DESC""", (uid,))]

    def renomear_caderno(self, uid: int, caderno_id: int, titulo: str) -> None:
        titulo = " ".join(titulo.split())[:80]
        if titulo:
            self._escrever("UPDATE cadernos SET titulo=? WHERE id=? AND usuario_id=?", (titulo, caderno_id, uid))

    def excluir_caderno(self, uid: int, caderno_id: int) -> None:
        self._escrever("DELETE FROM cadernos WHERE id=? AND usuario_id=?", (caderno_id, uid))

    def cadernos_criados_hoje(self, uid: int) -> int:
        return self._um("SELECT COUNT(*) AS n FROM cadernos WHERE usuario_id=? AND "
                        "date(criado_em,'unixepoch','localtime')=date('now','localtime')", (uid,))["n"]

    # ------------------------------------------------------------ chat

    def salvar_mensagem(self, caderno_id: int, pergunta: str, r: dict, consumiu: bool) -> None:
        self._escrever(
            "INSERT INTO mensagens (caderno_id, pergunta, resposta, fontes, sem_base, consumiu, ts) VALUES (?,?,?,?,?,?,?)",
            (caderno_id, pergunta, r["resposta"], json.dumps(r["fontes"], ensure_ascii=False),
             int(r["sem_base"]), int(consumiu), time.time()))

    def listar_mensagens(self, caderno_id: int) -> list[dict]:
        return [{"pergunta": m["pergunta"], "resposta": m["resposta"], "fontes": json.loads(m["fontes"]),
                 "sem_base": bool(m["sem_base"])}
                for m in self._todos("SELECT * FROM mensagens WHERE caderno_id=? ORDER BY id", (caderno_id,))]

    def perguntas_consumidas(self, caderno_id: int) -> int:
        return self._um("SELECT COALESCE(SUM(consumiu),0) AS n FROM mensagens WHERE caderno_id=?", (caderno_id,))["n"]

    # ------------------------------------------------------------ quiz

    def salvar_resultado_quiz(self, caderno_id: int, nota: float, acertos: int, total: int) -> None:
        self._escrever("INSERT INTO resultados_quiz (caderno_id, nota, acertos, total, ts) VALUES (?,?,?,?,?)",
                       (caderno_id, nota, acertos, total, time.time()))

    def resultados_quiz(self, caderno_id: int) -> list[dict]:
        return [dict(r) for r in self._todos(
            "SELECT nota, acertos, total, ts FROM resultados_quiz WHERE caderno_id=? ORDER BY id DESC", (caderno_id,))]

    # ------------------------------------------------------------ estatísticas do usuário

    def estatisticas(self, uid: int) -> dict:
        r = self._um("""
            SELECT (SELECT COUNT(*) FROM cadernos WHERE usuario_id=:u) AS cadernos,
                   (SELECT COUNT(*) FROM resultados_quiz q JOIN cadernos c ON c.id=q.caderno_id WHERE c.usuario_id=:u) AS quizzes,
                   (SELECT ROUND(AVG(q.nota),1) FROM resultados_quiz q JOIN cadernos c ON c.id=q.caderno_id WHERE c.usuario_id=:u) AS media,
                   (SELECT COUNT(*) FROM mensagens m JOIN cadernos c ON c.id=m.caderno_id WHERE c.usuario_id=:u) AS perguntas
            """, {"u": uid})
        return dict(r)
