"""
conftest.py — o que toda a suíte compartilha.

Três decisões sustentam o desenho daqui, e cada uma resolve um problema concreto
do código que está sendo testado:

1. `banco.CAMINHO_BANCO` é lido DENTRO de `conectar()` (banco.py), e `app.py`
   sempre chama `banco.conectar()` pelo atributo do módulo. Trocar esse atributo
   redireciona o fluxo inteiro — API, `com_banco`, `preparar()` — sem que o
   servidor precise de nenhuma refatoração para ser testável.

2. `app.py` resolve a chave de sessão em TEMPO DE IMPORT e, se a variável de
   ambiente não estiver posta, CRIA `backend/.chave-sessao`. Rodar a suíte não
   pode deixar rastro no repositório, então a variável é posta antes do import.

3. O custo de preparar um banco é o PBKDF2, não o SQLite: `_semear_contas` faz
   dois `generate_password_hash`, e cada um leva quase um segundo. Por isso o
   banco é preparado UMA vez por sessão e depois copiado por teste — cópia de
   arquivo custa um milissegundo, e o isolamento continua total.
"""

import os
import shutil
from functools import lru_cache
from types import SimpleNamespace

import pytest

# Antes de `import app` — ver a decisão 2 acima.
os.environ.setdefault("ETRILHA_SECRET", "chave-de-teste-fixa-nao-usar-em-producao")

import app as aplicacao  # noqa: E402
import banco  # noqa: E402

SENHA_PADRAO = "senha-de-teste"


@lru_cache(maxsize=None)
def _hash_de(senha: str) -> str:
    """
    PBKDF2 é lento de propósito, e é isso que o torna o item mais caro da suíte.
    Como as contas de teste compartilham a mesma senha, o hash é calculado uma
    vez só. O sal repetido não incomoda: nada aqui sai da pasta temporária.
    """
    from werkzeug.security import generate_password_hash

    return generate_password_hash(senha)


# --------------------------------------------------------------------------- #
# Banco
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="session")
def banco_molde(tmp_path_factory):
    """
    Prepara um banco completo uma única vez e devolve o caminho dele.

    O `wal_checkpoint(TRUNCATE)` não é detalhe: a conexão usa
    `PRAGMA journal_mode = WAL` (banco.py), então parte dos dados recém-gravados
    ainda está no arquivo `-wal`. Copiar só o `.db` sem o checkpoint produziria
    um banco pela metade, e o erro apareceria como uma tabela vazia num teste
    qualquer, longe da causa.
    """
    molde = tmp_path_factory.mktemp("banco") / "molde.db"

    original = banco.CAMINHO_BANCO
    banco.CAMINHO_BANCO = molde
    try:
        credenciais = banco.preparar(recriar=True)
        conexao = banco.conectar()
        try:
            conexao.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            conexao.close()
    finally:
        banco.CAMINHO_BANCO = original

    return SimpleNamespace(caminho=molde, credenciais=credenciais)


@pytest.fixture
def bd(banco_molde, tmp_path, monkeypatch):
    """Uma cópia intocada do molde para cada teste. O monkeypatch desfaz sozinho."""
    copia = tmp_path / "teste.db"
    shutil.copy2(banco_molde.caminho, copia)
    monkeypatch.setattr(banco, "CAMINHO_BANCO", copia)
    return SimpleNamespace(caminho=copia, credenciais=banco_molde.credenciais)


@pytest.fixture
def conexao(bd):
    """Conexão crua, para os testes que precisam falar SQL direto com o banco."""
    con = banco.conectar()
    try:
        yield con
    finally:
        con.close()


# --------------------------------------------------------------------------- #
# Cliente HTTP
# --------------------------------------------------------------------------- #

@pytest.fixture
def cliente(bd):
    aplicacao.app.config["TESTING"] = True

    # O test client fala http://localhost. Se `SESSION_COOKIE_SECURE` virar True
    # por padrão, ele para de mandar o cookie e TODA a suíte de autorização passa
    # a falhar com 401 — sem dizer por quê. A afirmação abaixo transforma esse
    # modo de falhar num erro que se explica sozinho.
    assert aplicacao.app.config.get("SESSION_COOKIE_SECURE") is not True, (
        "SESSION_COOKIE_SECURE ligado por padrão: o test client não manda cookie "
        "por HTTP e a suíte de autorização quebraria inteira. Ligue a opção só "
        "quando a variável de ambiente ETRILHA_HTTPS estiver posta."
    )

    with aplicacao.app.test_client() as c:
        yield c


# --------------------------------------------------------------------------- #
# Contas
# --------------------------------------------------------------------------- #

@pytest.fixture
def primeiro_ponto(bd):
    conexao = banco.conectar()
    try:
        return banco.listar_pontos(conexao)[0]
    finally:
        conexao.close()


@pytest.fixture
def fabricar_conta(bd):
    """
    Cria uma conta com o papel pedido.

    A promoção é feita por SQL direto, e não por `PATCH /api/admin/usuarios/<id>`,
    de propósito: `criar_usuario` grava 'visitante' no INSERT (é a defesa contra
    escalada de privilégio no cadastro), e um fixture não pode depender da mesma
    rota que outros testes existem para verificar — senão um bug na rota deixaria
    de ser detectado por ter estragado o preparo, não a asserção.
    """
    contador = {"n": 0}

    def fabricar(papel="visitante", *, nome=None, email=None,
                 senha=SENHA_PADRAO, ponto_id=None, provisoria=False):
        contador["n"] += 1
        n = contador["n"]
        conexao = banco.conectar()
        try:
            usuario = banco.criar_usuario(
                conexao,
                nome=nome or f"Conta {papel} {n}",
                email=email or f"{papel}{n}@teste.ms",
                senha_hash=_hash_de(senha),
            )
            with banco.transacao(conexao):
                conexao.execute(
                    "UPDATE usuarios SET papel = ?, ponto_id = ?, senha_provisoria = ? "
                    "WHERE id = ?",
                    (papel, ponto_id, 1 if provisoria else 0, usuario["id"]),
                )
            conta = banco.obter_usuario(conexao, usuario["id"])
        finally:
            conexao.close()

        conta["senha"] = senha
        return conta

    return fabricar


@pytest.fixture
def entrar(cliente):
    """
    Abre sessão gravando o cookie direto, sem passar pelo login.

    Passar por `POST /api/sessao` custaria um `check_password_hash` — de novo o
    PBKDF2 — em cada teste que só precisa estar autenticado para chegar no que
    de fato quer verificar. O login de verdade tem os seus próprios testes, em
    `teste_api_contas.py`.
    """
    def _entrar(conta):
        with cliente.session_transaction() as sessao:
            sessao.clear()
            sessao["usuario_id"] = conta["id"]
        return conta
    return _entrar


@pytest.fixture
def visitante(fabricar_conta, entrar):
    return entrar(fabricar_conta("visitante"))


@pytest.fixture
def operador(fabricar_conta, entrar, primeiro_ponto):
    return entrar(fabricar_conta("operador", ponto_id=primeiro_ponto["id"]))


@pytest.fixture
def admin(fabricar_conta, entrar):
    return entrar(fabricar_conta("admin"))
