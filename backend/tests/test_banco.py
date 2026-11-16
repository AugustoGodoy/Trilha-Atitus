import pytest

from estudo_guiado import seguranca
from estudo_guiado.banco import Banco, ErroAutenticacao


@pytest.fixture
def banco(tmp_path):
    return Banco(str(tmp_path / "app.sqlite"))


@pytest.fixture
def ana(banco):
    return banco.criar_usuario("Ana Souza", "Ana@Atitus.edu.br", "senha1234")


def test_hash_de_senha_nao_guarda_texto_puro_e_verifica():
    h = seguranca.hash_senha("senha1234")
    assert "senha1234" not in h
    assert seguranca.verificar_senha("senha1234", h)
    assert not seguranca.verificar_senha("outra1234", h)
    assert seguranca.hash_senha("senha1234") != h  # salt aleatório


def test_cadastro_normaliza_email_e_rejeita_duplicado(banco, ana):
    assert ana["email"] == "ana@atitus.edu.br"
    with pytest.raises(ErroAutenticacao, match="Já existe"):
        banco.criar_usuario("Outra Ana", "ANA@atitus.edu.br", "senha1234")


@pytest.mark.parametrize("nome,email,senha,trecho", [
    ("A", "a@b.com", "senha1234", "nome"),
    ("Ana", "sem-arroba", "senha1234", "e-mail"),
    ("Ana", "a@b.com", "curta1", "8 caracteres"),
    ("Ana", "a@b.com", "somenteletras", "letras e números"),
])
def test_cadastro_valida_entradas(banco, nome, email, senha, trecho):
    with pytest.raises(ErroAutenticacao, match=trecho):
        banco.criar_usuario(nome, email, senha)


def test_login_correto_e_incorreto(banco, ana):
    assert banco.autenticar("ana@atitus.edu.br", "senha1234")["id"] == ana["id"]
    with pytest.raises(ErroAutenticacao, match="incorretos"):
        banco.autenticar("ana@atitus.edu.br", "errada123")
    with pytest.raises(ErroAutenticacao, match="incorretos"):
        banco.autenticar("naoexiste@atitus.edu.br", "senha1234")


def test_bloqueio_apos_falhas_seguidas_e_liberacao_com_sucesso(banco, ana):
    for _ in range(4):
        with pytest.raises(ErroAutenticacao, match="incorretos"):
            banco.autenticar("ana@atitus.edu.br", "errada123")
    assert banco.autenticar("ana@atitus.edu.br", "senha1234")  # sucesso zera a contagem
    for _ in range(5):
        with pytest.raises(ErroAutenticacao, match="incorretos"):
            banco.autenticar("ana@atitus.edu.br", "errada123")
    with pytest.raises(ErroAutenticacao, match="Muitas tentativas"):
        banco.autenticar("ana@atitus.edu.br", "senha1234")


def test_sessao_guarda_apenas_o_hash_do_token(banco, ana):
    token = banco.criar_sessao(ana["id"])
    assert banco.usuario_da_sessao(token)["id"] == ana["id"]
    assert token not in str(banco._todos("SELECT * FROM sessoes")[0]["token_hash"])
    banco.encerrar_sessao(token)
    assert banco.usuario_da_sessao(token) is None
    assert banco.usuario_da_sessao("token-invalido") is None


def test_sessao_expirada_nao_autentica(banco, ana):
    token = banco.criar_sessao(ana["id"])
    banco._escrever("UPDATE sessoes SET expira_em = 1")
    assert banco.usuario_da_sessao(token) is None


def test_cadernos_sao_isolados_por_usuario(banco, ana):
    bia = banco.criar_usuario("Bia Lima", "bia@atitus.edu.br", "senha1234")
    cid = banco.registrar_caderno(ana["id"], "hash1", "Aula 1")
    assert banco.registrar_caderno(ana["id"], "hash1", "Aula 1") == cid  # mesmo material, mesmo caderno
    assert banco.caderno(bia["id"], cid) is None
    assert banco.listar_cadernos(bia["id"]) == []
    banco.excluir_caderno(bia["id"], cid)  # não apaga caderno alheio
    assert banco.caderno(ana["id"], cid)
    assert banco.cadernos_criados_hoje(ana["id"]) == 1


def test_chat_quiz_e_estatisticas(banco, ana):
    cid = banco.registrar_caderno(ana["id"], "h", "Aula 1")
    ok = {"resposta": "R", "fontes": [{"arquivo": "a.pdf", "pagina": 1}], "sem_base": False}
    recusa = {"resposta": "sem base", "fontes": [], "sem_base": True}
    banco.salvar_mensagem(cid, "p1", ok, consumiu=True)
    banco.salvar_mensagem(cid, "p2", recusa, consumiu=False)
    assert banco.perguntas_consumidas(cid) == 1
    msgs = banco.listar_mensagens(cid)
    assert [m["pergunta"] for m in msgs] == ["p1", "p2"] and msgs[0]["fontes"][0]["pagina"] == 1

    banco.salvar_resultado_quiz(cid, 6.0, 3, 5)
    banco.salvar_resultado_quiz(cid, 8.0, 4, 5)
    assert banco.resultados_quiz(cid)[0]["nota"] == 8.0
    est = banco.estatisticas(ana["id"])
    assert est == {"cadernos": 1, "quizzes": 2, "media": 7.0, "perguntas": 2}
    assert banco.listar_cadernos(ana["id"])[0]["melhor_nota"] == 8.0


def test_excluir_caderno_remove_dados_relacionados(banco, ana):
    cid = banco.registrar_caderno(ana["id"], "h", "Aula 1")
    banco.salvar_resultado_quiz(cid, 5.0, 1, 2)
    banco.excluir_caderno(ana["id"], cid)
    assert banco.resultados_quiz(cid) == []
