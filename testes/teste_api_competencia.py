"""
Competência por etapa (RF21): cada etapa só é registrada pelo tipo de ponto
que está com o aparelho nela.

Antes desta regra, o papel de operador valia para a cadeia inteira: o operador
de um ecoponto registrava "Em reciclagem" e "Processado" de um aparelho que
nunca saiu do ecoponto, e o certificado de destinação final saía assinado por
quem não reciclou nada. A tabela está em `modelo.COMPETENCIA`; aqui ela é
conferida pela API, que é onde vale.
"""

import json
from pathlib import Path

import pytest

import banco
import modelo

APARELHO = {"categoria": "cabos", "marca": "Teste", "pesoKg": 0.3}

#: Um ponto de cada tipo, da base de demonstração.
PONTO_DO_TIPO = {
    "ecoponto": "pt-cg-eco-norte",
    "cooperativa": "pt-cg-coop-reviver",
    "fabricante": "pt-cg-loja-tec",
    "pev": "pt-cg-shopping",
    "recicladora": "pt-cg-recicladora",
}

#: Para levar um item até a etapa anterior sem depender da regra em teste.
QUEM_REGISTRA = {etapa: tipos[0] for etapa, tipos in modelo.COMPETENCIA.items()}


def registrar(cliente):
    resposta = cliente.post("/api/itens", json=APARELHO)
    assert resposta.status_code == 201, resposta.get_json()
    return resposta.get_json()["codigo"]


def levar_ate(codigo, etapa_final):
    """Avança o item pelo banco, cada etapa no ponto competente."""
    conexao = banco.conectar()
    try:
        for etapa in modelo.IDS_ETAPAS[1:modelo.IDS_ETAPAS.index(etapa_final) + 1]:
            banco.registrar_evento(
                conexao, codigo, etapa=etapa,
                ponto_id=PONTO_DO_TIPO[QUEM_REGISTRA[etapa]],
                responsavel="Preparo do teste", observacao="",
            )
    finally:
        conexao.close()


def avancar(cliente, codigo, etapa, **corpo):
    return cliente.post(f"/api/itens/{codigo}/eventos", json={"etapa": etapa, **corpo})


def etapa_atual(cliente, codigo):
    return cliente.get(f"/api/itens/{codigo}/rastreio").get_json()["item"]["etapaAtual"]


# --------------------------------------------------------------------------- #
# A tabela
# --------------------------------------------------------------------------- #

def teste_toda_etapa_depois_do_registro_tem_quem_registre():
    assert list(modelo.COMPETENCIA) == modelo.IDS_ETAPAS[1:]
    for etapa, tipos in modelo.COMPETENCIA.items():
        assert tipos, f"{etapa} ficaria sem ninguém que a registre"
        assert set(tipos) <= set(modelo.TIPOS_PONTO), etapa


def teste_so_a_recicladora_emite_o_certificado():
    """O certificado é a afirmação mais forte do sistema; tem um dono só."""
    assert modelo.COMPETENCIA["EM_RECICLAGEM"] == ("recicladora",)
    assert modelo.COMPETENCIA["PROCESSADO"] == ("recicladora",)


def teste_quem_despacha_e_quem_fez_a_triagem():
    """Sem isso a cadeia teria um elo que ninguém pode registrar."""
    assert modelo.COMPETENCIA["EM_TRANSPORTE"] == modelo.COMPETENCIA["EM_TRIAGEM"]


def teste_a_trilha_de_demonstracao_respeita_a_competencia():
    raiz = Path(modelo.__file__).resolve().parent.parent
    pontos = {p["id"]: p["tipo"] for p in
              json.loads((raiz / "dados" / "pontos.json").read_text(encoding="utf-8"))}
    itens = json.loads((raiz / "dados" / "itens-demo.json").read_text(encoding="utf-8"))
    for item in itens:
        for etapa, _horas, ponto, _responsavel in item["trilha"][1:]:
            assert modelo.pode_registrar(etapa, pontos[ponto]), (
                f"{item['codigo']}: {etapa} registrada em {ponto} ({pontos[ponto]})"
            )


def teste_todos_os_pontos_da_base_tem_tipo_conhecido():
    raiz = Path(modelo.__file__).resolve().parent.parent
    pontos = json.loads((raiz / "dados" / "pontos.json").read_text(encoding="utf-8"))
    assert {p["tipo"] for p in pontos} <= set(modelo.TIPOS_PONTO)


# --------------------------------------------------------------------------- #
# A matriz inteira, pela API: cada tipo de ponto contra cada etapa
# --------------------------------------------------------------------------- #

MATRIZ = [(tipo, etapa) for tipo in PONTO_DO_TIPO for etapa in modelo.COMPETENCIA]


@pytest.mark.parametrize("tipo,etapa", MATRIZ, ids=[f"{t}-{e}" for t, e in MATRIZ])
def teste_operador_registra_so_as_etapas_do_seu_tipo_de_ponto(
    cliente, fabricar_conta, entrar, visitante, tipo, etapa
):
    codigo = registrar(cliente)
    anterior = modelo.IDS_ETAPAS[modelo.IDS_ETAPAS.index(etapa) - 1]
    if anterior != modelo.PRIMEIRA_ETAPA:
        levar_ate(codigo, anterior)

    entrar(fabricar_conta("operador", ponto_id=PONTO_DO_TIPO[tipo]))
    resposta = avancar(cliente, codigo, etapa)

    if tipo in modelo.COMPETENCIA[etapa]:
        assert resposta.status_code == 201, resposta.get_json()
        assert etapa_atual(cliente, codigo) == etapa
    else:
        assert resposta.status_code == 403, resposta.get_json()
        assert resposta.get_json()["competencia"] is True
        assert etapa_atual(cliente, codigo) == anterior


# --------------------------------------------------------------------------- #
# Casos que a matriz não mostra
# --------------------------------------------------------------------------- #

def teste_a_recusa_explica_quem_registra(cliente, operador, visitante, fabricar_conta, entrar):
    entrar(visitante)
    codigo = registrar(cliente)
    levar_ate(codigo, "EM_TRANSPORTE")
    entrar(operador)
    erro = avancar(cliente, codigo, "EM_RECICLAGEM").get_json()["erro"]
    assert "recicladora credenciada" in erro
    assert "ecoponto municipal" in erro


def teste_a_maquina_de_estados_responde_antes_da_competencia(cliente, operador):
    """Pular etapa continua sendo 400 com o motivo da transição, não 403."""
    codigo = registrar(cliente)
    resposta = avancar(cliente, codigo, "PROCESSADO")
    assert resposta.status_code == 400
    assert "pular" in resposta.get_json()["erro"]


def teste_operador_sem_ponto_nao_registra_nada(cliente, fabricar_conta, entrar, visitante):
    codigo = registrar(cliente)
    entrar(fabricar_conta("operador", ponto_id=None))
    resposta = avancar(cliente, codigo, "COLETADO")
    assert resposta.status_code == 403
    assert resposta.get_json()["competencia"] is True
    assert "vinculada a um ponto" in resposta.get_json()["erro"]


def teste_operador_sem_ponto_nao_escolhe_a_recicladora_pelo_corpo(
    cliente, fabricar_conta, entrar, visitante
):
    """Se o corpo valesse, bastaria mandar o id da recicladora."""
    codigo = registrar(cliente)
    levar_ate(codigo, "EM_TRANSPORTE")
    entrar(fabricar_conta("operador", ponto_id=None))
    resposta = avancar(cliente, codigo, "EM_RECICLAGEM", pontoId=PONTO_DO_TIPO["recicladora"])
    assert resposta.status_code == 403
    assert etapa_atual(cliente, codigo) == "EM_TRANSPORTE"


def teste_ponto_do_corpo_nao_amplia_a_competencia_do_operador(
    cliente, operador, visitante, entrar
):
    entrar(visitante)
    codigo = registrar(cliente)
    levar_ate(codigo, "EM_TRANSPORTE")
    entrar(operador)
    resposta = avancar(cliente, codigo, "EM_RECICLAGEM", pontoId=PONTO_DO_TIPO["recicladora"])
    assert resposta.status_code == 403


def teste_admin_tambem_passa_pela_tabela(cliente, admin):
    """O admin escolhe o local, mas o local precisa ser o competente."""
    codigo = registrar(cliente)
    levar_ate(codigo, "EM_TRANSPORTE")

    recusada = avancar(cliente, codigo, "EM_RECICLAGEM", pontoId=PONTO_DO_TIPO["ecoponto"])
    assert recusada.status_code == 403

    aceita = avancar(cliente, codigo, "EM_RECICLAGEM", pontoId=PONTO_DO_TIPO["recicladora"])
    assert aceita.status_code == 201
    assert aceita.get_json()["pontoId"] == PONTO_DO_TIPO["recicladora"]


def teste_admin_sem_local_e_recusado(cliente, admin):
    """Um elo sem local não diz onde o aparelho estava nem quem o tinha."""
    codigo = registrar(cliente)
    resposta = avancar(cliente, codigo, "COLETADO")
    assert resposta.status_code == 400
    assert "Informe o ponto" in resposta.get_json()["erro"]


def teste_a_recusa_nao_deixa_rastro(cliente, operador):
    codigo = registrar(cliente)
    levar_ate(codigo, "EM_TRANSPORTE")
    antes = cliente.get(f"/api/itens/{codigo}/rastreio").get_json()["eventos"]
    avancar(cliente, codigo, "EM_RECICLAGEM")
    depois = cliente.get(f"/api/itens/{codigo}/rastreio").get_json()["eventos"]
    assert depois == antes


def teste_a_carga_cria_um_operador_em_cada_ponta_da_cadeia(bd):
    """Sem a conta da recicladora, a demonstração do ciclo dependeria do admin."""
    conexao = banco.conectar()
    try:
        linhas = conexao.execute(
            "SELECT p.tipo FROM usuarios u JOIN pontos p ON p.id = u.ponto_id "
            "WHERE u.papel = 'operador'"
        ).fetchall()
    finally:
        conexao.close()
    assert sorted(l["tipo"] for l in linhas) == ["ecoponto", "recicladora"]
