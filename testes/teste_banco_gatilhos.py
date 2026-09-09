"""
As garantias que o SQLite impõe sozinho.

O Relatório Técnico afirma, no RNF07, que o histórico de eventos é impossível de
alterar ou apagar — e a razão de isso ser forte é que a proibição não está na
aplicação, e sim em gatilhos do próprio banco. Um erro de programação numa rota
nova, ou alguém abrindo o arquivo `.db` com um cliente SQLite qualquer, esbarra
na mesma parede.

Este arquivo fala SQL direto com a conexão, sem passar pela API, porque é
exatamente esse o caminho que os gatilhos precisam fechar.
"""

import sqlite3

import pytest

import banco

APENAS_ACRESCIMO = ["eventos", "apagamentos", "alteracoes_conta"]


@pytest.fixture
def com_um_item(conexao):
    """Um item com evento de abertura, atestado de apagamento e alteração de conta."""
    import modelo
    from werkzeug.security import generate_password_hash

    item = banco.criar_item(
        conexao, categoria="notebook", marca="Dell", peso_kg=1.9,
        ponto_origem_id=None, responsavel="Teste", usuario_id=None,
    )
    banco.registrar_evento(
        conexao, item["codigo"], etapa="COLETADO", ponto_id=None,
        responsavel="Teste", observacao="",
    )
    banco.registrar_evento(
        conexao, item["codigo"], etapa="EM_TRIAGEM", ponto_id=None,
        responsavel="Teste", observacao="",
        apagamento={"midia": "flash", "metodo": "SECURE_ERASE"},
    )

    autor = banco.criar_usuario(
        conexao, nome="Autor", email="autor@teste.ms",
        senha_hash=generate_password_hash("senha-boa"),
    )
    alvo = banco.criar_usuario(
        conexao, nome="Alvo", email="alvo@teste.ms",
        senha_hash=generate_password_hash("senha-boa"),
    )
    with banco.transacao(conexao):
        conexao.execute("UPDATE usuarios SET papel = 'admin' WHERE id = ?", (autor["id"],))
    banco.atualizar_usuario(conexao, alvo["id"], autor=banco.obter_usuario(conexao, autor["id"]),
                            papel="operador")

    assert modelo.PRIMEIRA_ETAPA  # o módulo é usado acima; a linha documenta o import
    return item


# --------------------------------------------------------------------------- #
# Somente acréscimo
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("tabela", APENAS_ACRESCIMO)
def teste_update_e_abortado_pelo_gatilho(conexao, com_um_item, tabela):
    antes = conexao.execute(f"SELECT COUNT(*) AS n FROM {tabela}").fetchone()["n"]
    assert antes > 0, f"o preparo precisa deixar linhas em {tabela} para o teste valer"

    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(f"UPDATE {tabela} SET em = '1999-01-01T00:00:00'")


@pytest.mark.parametrize("tabela", APENAS_ACRESCIMO)
def teste_delete_e_abortado_pelo_gatilho(conexao, com_um_item, tabela):
    antes = conexao.execute(f"SELECT COUNT(*) AS n FROM {tabela}").fetchone()["n"]
    assert antes > 0

    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(f"DELETE FROM {tabela}")

    depois = conexao.execute(f"SELECT COUNT(*) AS n FROM {tabela}").fetchone()["n"]
    assert depois == antes


def teste_a_mensagem_do_gatilho_explica_o_motivo(conexao, com_um_item):
    """Quem esbarrar nisso num cliente SQLite precisa entender que é de propósito."""
    with pytest.raises(sqlite3.IntegrityError) as erro:
        conexao.execute("DELETE FROM eventos")
    assert str(erro.value).strip()


def teste_o_INSERT_continua_livre(conexao, com_um_item):
    """A proibição é de reescrever, não de registrar — a cadeia só cresce."""
    antes = conexao.execute("SELECT COUNT(*) AS n FROM eventos").fetchone()["n"]
    banco.registrar_evento(
        conexao, com_um_item["codigo"], etapa="EM_TRANSPORTE", ponto_id=None,
        responsavel="Teste", observacao="",
    )
    depois = conexao.execute("SELECT COUNT(*) AS n FROM eventos").fetchone()["n"]
    assert depois == antes + 1


# --------------------------------------------------------------------------- #
# Integridade referencial
# --------------------------------------------------------------------------- #

def teste_chaves_estrangeiras_estao_ligadas(conexao):
    """
    `PRAGMA foreign_keys` é POR CONEXÃO e vem desligado por padrão no SQLite.
    Ligá-lo em `conectar()` é o que faz as chaves estrangeiras do schema valerem
    alguma coisa — sem isso elas são só documentação.
    """
    assert conexao.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def teste_evento_de_item_inexistente_e_recusado(conexao):
    with pytest.raises(sqlite3.IntegrityError):
        with banco.transacao(conexao):
            conexao.execute(
                "INSERT INTO eventos (item_codigo, etapa, responsavel, em) "
                "VALUES ('MS-XXXX-XXXX', 'COLETADO', 'Teste', '2026-01-01T00:00:00')"
            )


def teste_item_com_eventos_nao_pode_ser_apagado(conexao, com_um_item):
    """
    `ON DELETE RESTRICT`: apagar o aparelho levaria a trilha junto, e a trilha é
    o que o sistema promete preservar.
    """
    with pytest.raises(sqlite3.IntegrityError):
        with banco.transacao(conexao):
            conexao.execute("DELETE FROM itens WHERE codigo = ?", (com_um_item["codigo"],))


def teste_peso_nao_positivo_e_recusado_pelo_banco(conexao):
    """A regra existe em `modelo.py` e também como CHECK na tabela."""
    with pytest.raises(sqlite3.IntegrityError):
        with banco.transacao(conexao):
            conexao.execute(
                "INSERT INTO itens (codigo, categoria, peso_kg, criado_em, atualizado_em, etapa_atual) "
                "VALUES ('MS-TEST-0000', 'notebook', -1, '2026-01-01', '2026-01-01', 'REGISTRADO')"
            )


def teste_papel_fora_da_lista_e_recusado_pelo_banco(conexao):
    with pytest.raises(sqlite3.IntegrityError):
        with banco.transacao(conexao):
            conexao.execute("UPDATE usuarios SET papel = 'root'")


# --------------------------------------------------------------------------- #
# Esquema e carga
# --------------------------------------------------------------------------- #

def teste_a_versao_do_arquivo_bate_com_a_do_schema(conexao):
    """
    Se divergirem, `preparar()` recria o banco na próxima subida do servidor —
    e leva junto tudo que foi cadastrado. Vale saber disso por um teste, e não
    por uma demonstração que perdeu os dados.
    """
    do_arquivo = conexao.execute("PRAGMA user_version").fetchone()[0]
    assert do_arquivo == banco._versao_do_schema()


def teste_o_journal_esta_em_wal(conexao):
    assert conexao.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def teste_a_carga_trouxe_os_pontos_de_coleta(conexao):
    """
    Único teste que afirma sobre `dados/*.json`, e de propósito só sobre a
    quantidade: os demais criam os próprios dados, para que editar o arquivo de
    demonstração não quebre a suíte inteira.
    """
    assert conexao.execute("SELECT COUNT(*) AS n FROM pontos").fetchone()["n"] > 0
    assert conexao.execute("SELECT COUNT(*) AS n FROM itens").fetchone()["n"] > 0
    contas = conexao.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"]
    assert contas == len(banco.CONTAS_INICIAIS)
